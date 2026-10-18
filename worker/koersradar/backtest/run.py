"""Backtest van trend-pullback op de Parquet-historie, per instrument en periode.

Periodes (plan: train/test op tijd, hold-out pas aan het eind):
  train         vanaf --start tot --split
  test          --split tot --holdout
  walk_forward  opeenvolgende blokken van --wf-months over train + test
  holdout       vanaf --holdout; alleen met --include-holdout

Voorbeelden:
  python -m koersradar.backtest.run --interval 1h
  python -m koersradar.backtest.run --interval 15m --symbols BTC/USDT ETH/USDT --random-runs 50
  python -m koersradar.backtest.run --interval 1h --save-db     # schrijft naar backtest_runs
"""

import argparse
import json
import logging
import os
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from koersradar.backtest.engine import simulate, trades_frame
from koersradar.backtest.metrics import (
    RISK_FRAC,
    buy_and_hold,
    percentile_rank,
    random_entry,
    summarize,
)
from koersradar.config import CostModel, load_costs, load_instruments
from koersradar.ingest.store import data_dir, read_history
from koersradar.strategies import trend_pullback as tp

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Period:
    kind: str  # train | test | walk_forward | holdout
    start: pd.Timestamp
    end: pd.Timestamp  # exclusief

    @property
    def label(self) -> str:
        return f"{self.kind} {self.start:%Y-%m-%d} – {self.end:%Y-%m-%d}"


def make_periods(
    first: pd.Timestamp,
    last: pd.Timestamp,
    split: pd.Timestamp,
    holdout: pd.Timestamp,
    wf_months: int,
    include_holdout: bool,
) -> list[Period]:
    stop = min(holdout, last)
    periods = [Period("train", first, min(split, stop)), Period("test", split, stop)]
    cur = first
    while cur < stop:
        nxt = min(cur + pd.DateOffset(months=wf_months), stop)
        periods.append(Period("walk_forward", cur, nxt))
        cur = nxt
    if include_holdout and last > holdout:
        periods.append(Period("holdout", holdout, last))
    return [p for p in periods if p.end > p.start]


def params(costs: CostModel) -> dict:
    return {
        "min_history": tp.MIN_HISTORY,
        "rsi_dip": tp.RSI_DIP,
        "rsi_max_entry": tp.RSI_MAX_ENTRY,
        "dip_lookback": tp.DIP_LOOKBACK,
        "stop_atr": tp.STOP_ATR,
        "target_r": tp.TARGET_R,
        "min_rr": tp.MIN_RR,
        "risk_frac": RISK_FRAC,
        "costs": asdict(costs),
        "execution": "signaal op slot t, instap op open t+1; stop vóór doel in één candle",
    }


def run_symbol(
    symbol: str, interval: str, source: str, costs: CostModel, periods_args: dict, random_runs: int
) -> list[dict]:
    df = read_history(source, symbol, interval)
    if len(df) < tp.MIN_HISTORY + 10:
        log.warning("%s %s: te weinig historie (%d candles)", symbol, interval, len(df))
        return []
    df = df.reset_index(drop=True)
    sig = tp.evaluate_all(df, costs)
    times = pd.DatetimeIndex(df["open_time"])
    periods = make_periods(times[0], times[-1] + (times[-1] - times[-2]), **periods_args)

    rows = []
    for p in periods:
        start, end = int(times.searchsorted(p.start)), int(times.searchsorted(p.end))
        if end - start < 2:
            continue
        res = simulate(df, sig, costs, start, end)
        metrics = summarize(res)
        atr0 = float(np.nan_to_num(sig["atr"].iloc[max(start, tp.MIN_HISTORY)]))
        bench: dict = {"buy_and_hold": buy_and_hold(df, costs, start, end, atr0)}
        if p.kind != "walk_forward" and random_runs > 0:
            rnd = random_entry(
                df,
                sig,
                costs,
                start,
                end,
                int(metrics["trades"] or 0),
                tp.MIN_HISTORY,
                runs=random_runs,
            )
            if rnd:
                metrics["beats_random_share"] = percentile_rank(
                    metrics["avg_r"], rnd.pop("_avg_r_runs")
                )
            bench["random_entry"] = rnd
        rows.append(
            {
                "symbol": symbol,
                "interval": interval,
                "period_kind": p.kind,
                "period_start": p.start.isoformat(),
                "period_end": p.end.isoformat(),
                "metrics": metrics,
                "benchmarks": bench,
                "trades": trades_frame(res.trades),
            }
        )
    return rows


def _fmt(v: float | None, pct: bool = False, dec: int = 2, sign: bool = False) -> str:
    """Getal voor de terminal; alleen ASCII, omdat de Windows-console anders tekens verminkt."""
    if v is None:
        return "-"
    if isinstance(v, float) and not np.isfinite(v):
        return "inf"
    if pct:
        return f"{v * 100:+.1f}%" if sign else f"{v * 100:.1f}%"
    return f"{v:+.{dec}f}" if sign else f"{v:.{dec}f}"


def print_table(rows: list[dict], kinds: tuple[str, ...]) -> None:
    head = (
        f"{'instrument':10} {'periode':34} {'trades':>6} {'win':>6} {'gem. R':>7} "
        f"{'PF':>5} {'rendement':>10} {'max DD':>8} {'B&H':>9} {'random R':>9} {'> random':>8}"
    )
    print(head)
    print("-" * len(head))
    for r in rows:
        if r["period_kind"] not in kinds:
            continue
        m, b = r["metrics"], r["benchmarks"]
        rnd = b.get("random_entry") or {}
        period = f"{r['period_kind']} {r['period_start'][:10]} t/m {r['period_end'][:10]}"
        bh = b["buy_and_hold"]["return_pct"]
        print(
            f"{r['symbol']:10} {period:34} "
            f"{m['trades']:>6} {_fmt(m['winrate'], True):>6} {_fmt(m['avg_r'], sign=True):>7} "
            f"{_fmt(m['profit_factor']):>5} {_fmt(m['return_pct'], True, sign=True):>10} "
            f"{_fmt(m['max_drawdown_pct'], True, sign=True):>8} {_fmt(bh, True, sign=True):>9} "
            f"{_fmt(rnd.get('avg_r_median'), sign=True):>9} "
            f"{_fmt(m.get('beats_random_share'), True):>8}"
        )


def pooled(rows: list[dict], kind: str) -> dict | None:
    """Alle trades van alle instrumenten in één periode-soort samen."""
    tr = [r["trades"] for r in rows if r["period_kind"] == kind and not r["trades"].empty]
    if not tr:
        return None
    r = pd.concat(tr)["r_multiple"].to_numpy(dtype=float)
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {
        "trades": len(r),
        "winrate": float((r > 0).mean()),
        "avg_r": float(r.mean()),
        "profit_factor": float(gains / losses) if losses > 0 else None,
    }


def _records(rows: list[dict], interval: str, params_by_symbol: dict[str, dict], ids: dict) -> list:
    """Regels voor public.backtest_runs; oneindige waarden (PF zonder verlies) worden null."""

    def clean(d: dict) -> dict:
        return {
            k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in d.items()
        }

    return [
        {
            "strategy_version": tp.VERSION,
            "instrument_id": ids.get(r["symbol"]),
            "interval": interval,
            "params": params_by_symbol[r["symbol"]],
            "period_kind": r["period_kind"],
            "period_start": r["period_start"],
            "period_end": r["period_end"],
            "metrics": clean(r["metrics"]),
            "benchmarks": r["benchmarks"],
        }
        for r in rows
    ]


def _save_postgres(rows: list[dict], interval: str, params_by_symbol: dict[str, dict]) -> int:
    from koersradar.db import connect

    with connect() as conn, conn.cursor() as cur:
        cur.execute("select symbol, id from public.instruments")
        ids: dict[str, int] = dict(cur.fetchall())
        for rec in _records(rows, interval, params_by_symbol, ids):
            cur.execute(
                """insert into public.backtest_runs
                   (strategy_version, instrument_id, interval, params, period_kind,
                    period_start, period_end, metrics, benchmarks)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    *[rec[k] for k in ("strategy_version", "instrument_id", "interval")],
                    json.dumps(rec["params"]),
                    *[rec[k] for k in ("period_kind", "period_start", "period_end")],
                    json.dumps(rec["metrics"]),
                    json.dumps(rec["benchmarks"]),
                ),
            )
        conn.commit()
    return len(rows)


def _save_rest(rows: list[dict], interval: str, params_by_symbol: dict[str, dict]) -> int:
    """Via de Supabase REST-API met de service-key; één verzoek, dus één created_at."""
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def call(method: str, path: str, body: object | None = None) -> object:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{url}/rest/v1/{path}", data, headers, method=method)
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None

    found = call("GET", "instruments?select=id,symbol")
    ids = {i["symbol"]: i["id"] for i in found} if isinstance(found, list) else {}
    call("POST", "backtest_runs", _records(rows, interval, params_by_symbol, ids))
    return len(rows)


def save_db(rows: list[dict], interval: str, params_by_symbol: dict[str, dict]) -> int:
    """Postgres als DATABASE_URL er is, anders de REST-API met de service-key."""
    if os.environ.get("DATABASE_URL"):
        return _save_postgres(rows, interval, params_by_symbol)
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return _save_rest(rows, interval, params_by_symbol)
    raise RuntimeError("Opslaan vraagt DATABASE_URL of SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--interval", default="1h", choices=["15m", "1h"])
    ap.add_argument("--symbols", nargs="*", help="standaard: alle crypto uit instruments.yaml")
    ap.add_argument("--split", default="2025-01-01", help="begin testperiode")
    ap.add_argument(
        "--holdout", default="2026-01-01", help="begin hold-out (standaard niet getest)"
    )
    ap.add_argument("--include-holdout", action="store_true")
    ap.add_argument("--wf-months", type=int, default=3)
    ap.add_argument("--random-runs", type=int, default=100)
    ap.add_argument("--save-db", action="store_true", help="resultaten in public.backtest_runs")
    args = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    costs_all = load_costs()
    instruments = [
        i
        for i in load_instruments()
        if args.interval in i.intervals
        and (i.symbol in args.symbols if args.symbols else i.market == "crypto")
    ]
    pargs = {
        "split": pd.Timestamp(args.split, tz=UTC),
        "holdout": pd.Timestamp(args.holdout, tz=UTC),
        "wf_months": args.wf_months,
        "include_holdout": args.include_holdout,
    }

    rows: list[dict] = []
    param_by_symbol: dict[str, dict] = {}
    for ins in instruments:
        costs = costs_all[ins.source]
        log.info("%s %s", ins.symbol, args.interval)
        rows += run_symbol(ins.symbol, args.interval, ins.source, costs, pargs, args.random_runs)
        param_by_symbol[ins.symbol] = params(costs)

    if not rows:
        print("Geen resultaten: draai eerst de backfill (python -m koersradar.ingest.backfill).")
        return

    print(
        f"\nStrategie {tp.VERSION} op {args.interval}, risico {RISK_FRAC:.0%} per trade, na kosten"
    )
    print()
    kinds = ("train", "test", "holdout")
    print_table(rows, kinds)
    print()
    for kind in kinds:
        pool = pooled(rows, kind)
        if pool:
            print(
                f"Alle instrumenten samen, {kind:5}: {pool['trades']} trades, "
                f"winrate {_fmt(pool['winrate'], True)}, gem. R {_fmt(pool['avg_r'], sign=True)}, "
                f"PF {_fmt(pool['profit_factor'])}"
            )

    out_dir = data_dir() / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    report = {
        "strategy_version": tp.VERSION,
        "interval": args.interval,
        "created_at": stamp,
        "params": param_by_symbol,
        "runs": [{k: v for k, v in r.items() if k != "trades"} for r in rows],
        "pooled": {k: pooled(rows, k) for k in ("train", "test", "walk_forward", "holdout")},
    }
    path = out_dir / f"backtest-{args.interval}-{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str, allow_nan=True))
    trades = pd.concat(
        [
            r["trades"].assign(symbol=r["symbol"], period=r["period_kind"])
            for r in rows
            if not r["trades"].empty
        ]
        or [pd.DataFrame()]
    )
    trades.to_csv(path.with_suffix(".trades.csv"), index=False)
    print(f"\nRapport: {path}")

    if args.save_db:
        n = save_db(rows, args.interval, param_by_symbol)
        print(f"{n} regels opgeslagen in backtest_runs")


if __name__ == "__main__":
    main()
