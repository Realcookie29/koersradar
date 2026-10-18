"""Automatisch paper trading: de koopsignalen van de scanner met nepgeld naspelen.

Zo testen we de regels vanaf nu vooruit, op data die nog niemand had kunnen bekijken.
Uitvoering volgt precies de backtest-engine (`backtest.engine.simulate`): instap op de open
van de candle na het signaal, stop gaat voor doel, uit op de volgende open als EMA 50
onder EMA 200 zakt, en dezelfde kosten.

Risicoregels (docs/plan.md):
- 1% van het (virtuele) vermogen risico per trade.
- Na 3% verlies op één dag (Amsterdamse tijd) geen nieuwe trades meer die dag.
- Maximaal 5 open posities, en per instrument maar één tegelijk.

Elk signaal krijgt één keer een besluit (geopend of overgeslagen, met reden) in
`paper_decisions`. Een signaal kan dus nooit later alsnog tegen een oude koers worden geopend.
Wordt een signaal te laat verwerkt (worker lag stil), dan slaan we het over.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg

from koersradar import db
from koersradar.backtest.engine import Trade, sell_proceeds, simulate
from koersradar.config import CostModel, load_costs
from koersradar.strategies import trend_pullback as tp
from koersradar.timeutils import interval_delta, utcnow

log = logging.getLogger(__name__)

START_EQUITY = 10_000.0
RISK_FRAC = 0.01
MAX_DAILY_LOSS = 0.03
MAX_OPEN = 5
LOOKBACK = timedelta(days=2)  # zo oude signalen pakken we nog op om een besluit te nemen
MAX_LATE_BARS = 3  # instap meer dan zoveel candles geleden: te laat verwerkt
WINDOW = 300  # candles vóór het signaal, genoeg voor EMA 200
TZ = ZoneInfo("Europe/Amsterdam")

EXIT_REASON = {"stop": "stop", "doel": "target", "ongeldig": "invalidated"}


@dataclass(frozen=True)
class Outcome:
    status: Literal["wacht", "overgeslagen", "open", "gesloten"]
    trade: Trade | None = None
    atr: float = float("nan")


def replay(
    window: pd.DataFrame,
    signal_time: datetime,
    stop: float,
    target: float,
    costs: CostModel,
) -> Outcome:
    """Speel één signaal na op de candles in `window` (gesloten candles, oplopend)."""
    times = pd.DatetimeIndex(window["open_time"])
    i = int(times.searchsorted(pd.Timestamp(signal_time)))
    if i >= len(times) or times[i] != pd.Timestamp(signal_time):
        return Outcome("overgeslagen")  # signaalcandle niet (meer) beschikbaar
    base = tp.evaluate_all(window, costs)
    trade = pd.Series(False, index=window.index)
    trade.iloc[i] = True
    sig = pd.DataFrame(
        {
            "trade": trade,
            "stop": stop,
            "target": target,
            "atr": base["atr"],
            "trend_ok": base["trend_ok"],
        },
        index=window.index,
    )
    res = simulate(window, sig, costs, start=i, end=len(window))
    atr = float(base["atr"].iloc[i])
    if res.skipped_gaps:
        return Outcome("overgeslagen", atr=atr)
    if not res.trades:
        return Outcome("wacht", atr=atr)  # volgende candle is er nog niet
    t = res.trades[0]
    return Outcome("open" if t.exit_reason == "einde" else "gesloten", t, atr)


def position_size(t: Trade, atr: float, costs: CostModel, equity: float) -> tuple[float, float]:
    """(aantal, risicobedrag) zodat een geraakte stop na kosten RISK_FRAC van het vermogen kost."""
    risk_amount = RISK_FRAC * equity
    per_unit = t.entry_price - sell_proceeds(t.stop, atr, costs)
    return (risk_amount / per_unit if per_unit > 0 else 0.0), risk_amount


def block_reason(
    instrument_id: int,
    open_instruments: set[int],
    equity: float,
    day_pnl: float,
) -> str | None:
    """Waarom een nieuwe trade niet mag, of None als het mag."""
    if instrument_id in open_instruments:
        return "er staat al een positie open in dit instrument"
    if len(open_instruments) >= MAX_OPEN:
        return f"al {MAX_OPEN} posities open"
    day_start = equity - day_pnl
    if day_pnl <= -MAX_DAILY_LOSS * day_start:
        return f"dagverlies van {MAX_DAILY_LOSS:.0%} bereikt"
    return None


def day_start(now: datetime) -> datetime:
    local = now.astimezone(TZ)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


# ---------- database ----------


def _window(
    conn: psycopg.Connection, instrument_id: int, interval: str, signal_time: datetime
) -> pd.DataFrame:
    df = db.recent_window(
        conn, instrument_id, interval, signal_time - WINDOW * interval_delta(interval)
    )
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df


def _decide(conn: psycopg.Connection, signal_id: int, outcome: str, reason: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """insert into public.paper_decisions (signal_id, outcome, reason)
               values (%s, %s, %s) on conflict (signal_id) do nothing""",
            (signal_id, outcome, reason),
        )


def _close(conn: psycopg.Connection, paper_id: int, t: Trade, size: float) -> float:
    pnl = (t.exit_price - t.entry_price) * size
    with conn.cursor() as cur:
        cur.execute(
            """update public.paper_trades set closed_at=%s, exit_price=%s, exit_reason=%s,
               pnl_after_costs=%s, r_multiple=%s where id=%s and closed_at is null""",
            (
                t.exit_time.to_pydatetime(),
                t.exit_raw,
                EXIT_REASON[t.exit_reason],
                pnl,
                t.r_multiple,
                paper_id,
            ),
        )
    return pnl


def _book(conn: psycopg.Connection) -> tuple[float, list[tuple[datetime, float]]]:
    """Vermogen (start + gerealiseerd resultaat) en de gesloten trades (tijd, resultaat)."""
    with conn.cursor() as cur:
        cur.execute(
            """select closed_at, pnl_after_costs from public.paper_trades
               where closed_at is not null"""
        )
        closed = [(r[0], float(r[1])) for r in cur.fetchall()]
    return START_EQUITY + sum(p for _, p in closed), closed


def run_paper(conn: psycopg.Connection, now: datetime | None = None) -> dict[str, int]:
    """Werk open paper trades bij en neem een besluit over nieuwe koopsignalen."""
    now = now or utcnow()
    costs_all = load_costs()
    counts = {"gesloten": 0, "geopend": 0, "overgeslagen": 0}

    with conn.cursor() as cur:
        cur.execute("select id, source from public.instruments")
        source = {int(r[0]): str(r[1]) for r in cur.fetchall()}

    # 1. Open trades bijwerken.
    with conn.cursor() as cur:
        cur.execute(
            """select p.id, p.size, s.instrument_id, s.interval, s.last_candle_at,
                      s.stop_loss, s.target
               from public.paper_trades p join public.signals s on s.id = p.signal_id
               where p.closed_at is null"""
        )
        open_rows = cur.fetchall()
    open_instruments: set[int] = set()
    for paper_id, size, ins_id, interval, sig_time, stop, target in open_rows:
        costs = costs_all[source[ins_id]]
        out = replay(_window(conn, ins_id, interval, sig_time), sig_time, stop, target, costs)
        if out.status == "gesloten" and out.trade is not None:
            _close(conn, paper_id, out.trade, float(size))
            counts["gesloten"] += 1
        else:
            open_instruments.add(int(ins_id))
    conn.commit()

    # 2. Besluit over nieuwe signalen, oudste eerst.
    equity, closed = _book(conn)
    today = day_start(now)
    day_pnl = sum(p for at, p in closed if at >= today)
    with conn.cursor() as cur:
        cur.execute(
            """select s.id, s.instrument_id, s.interval, s.last_candle_at, s.stop_loss, s.target
               from public.signals s join public.instruments i on i.id = s.instrument_id
               where s.decision = 'TRADE' and s.direction = 'long' and not i.experimental
                 and s.created_at >= %s
                 and not exists (select 1 from public.paper_decisions d where d.signal_id = s.id)
               order by s.last_candle_at, s.id""",
            (now - LOOKBACK,),
        )
        candidates = cur.fetchall()

    for sig_id, ins_id, interval, sig_time, stop, target in candidates:
        costs = costs_all[source[ins_id]]
        out = replay(_window(conn, ins_id, interval, sig_time), sig_time, stop, target, costs)
        if out.status == "wacht":
            continue
        reason: str | None
        if out.status == "overgeslagen" or out.trade is None:
            reason = "koers opende al voorbij stop of doel"
        elif out.trade.entry_time < now - MAX_LATE_BARS * interval_delta(interval):
            reason = "te laat verwerkt (worker lag stil)"
        else:
            reason = block_reason(int(ins_id), open_instruments, equity, day_pnl)
        if reason or out.trade is None:
            _decide(conn, sig_id, "skipped", reason)
            conn.commit()
            counts["overgeslagen"] += 1
            continue

        t = out.trade
        size, risk_amount = position_size(t, out.atr, costs, equity)
        with conn.cursor() as cur:
            cur.execute(
                """insert into public.paper_trades
                   (signal_id, opened_at, entry_price, size, risk_amount)
                   values (%s, %s, %s, %s, %s) returning id""",
                (sig_id, t.entry_time.to_pydatetime(), t.entry_raw, size, risk_amount),
            )
            row = cur.fetchone()
        assert row is not None
        _decide(conn, sig_id, "opened", None)
        counts["geopend"] += 1
        if out.status == "gesloten":  # al afgelopen sinds de vorige ronde
            pnl = _close(conn, int(row[0]), t, size)
            equity += pnl
            if t.exit_time.to_pydatetime() >= today:
                day_pnl += pnl
            counts["gesloten"] += 1
        else:
            open_instruments.add(int(ins_id))
        conn.commit()

    log.info("paper trading: %s", counts)
    return counts


def run_paper_round() -> None:
    """Eén ronde met een eigen verbinding; een fout mag de scanner niet stoppen."""
    try:
        with db.connect() as conn:
            run_paper(conn)
    except Exception:
        log.exception("paper trading faalde")
