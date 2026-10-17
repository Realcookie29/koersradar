"""Scanner: beoordeel elk instrument/interval met de strategie en sla het resultaat op.

Volgorde per instrument: venster laden -> kwaliteitscheck -> versheidspoort ->
strategie -> signaal opslaan (één per candle) -> AI-uitleg bij een TRADE.
"""

import json
import logging
from datetime import datetime

import pandas as pd
import psycopg

from koersradar import db
from koersradar.config import load_costs, load_instruments
from koersradar.explain.llm import explain
from koersradar.ingest.quality import assess
from koersradar.signals.freshness import freshness_gate
from koersradar.signals.model import Signal
from koersradar.sources.registry import get_source
from koersradar.strategies import trend_pullback
from koersradar.timeutils import interval_delta, utcnow

log = logging.getLogger(__name__)

WINDOW = 300  # candles; ruim genoeg voor EMA 200


def _insert_signal(
    conn: psycopg.Connection, instrument_id: int, run_id: int, s: Signal
) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """insert into public.signals
               (instrument_id, interval, decision, direction, entry, invalidation, stop_loss,
                target, rr_ratio, strength, facts, assumptions, no_trade_reason, data_source,
                last_candle_at, data_delay_s, cost_assumptions, liquidity_ok, strategy_version,
                scan_run_id)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               on conflict (instrument_id, interval, strategy_version, last_candle_at) do nothing
               returning id""",
            (
                instrument_id,
                s.interval,
                s.decision,
                s.direction,
                s.entry,
                s.invalidation,
                s.stop_loss,
                s.target,
                s.rr_ratio,
                s.strength,
                json.dumps([f.model_dump() for f in s.facts]),
                json.dumps(s.assumptions),
                s.no_trade_reason,
                s.data_source,
                s.last_candle_at,
                s.data_delay_s,
                s.cost_assumptions.model_dump_json(),
                s.liquidity_ok,
                s.strategy_version,
                run_id,
            ),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _save_explanation(conn: psycopg.Connection, signal_id: int, s: Signal) -> None:
    exp = explain(s)
    with conn.cursor() as cur:
        cur.execute(
            """update public.signals set explanation=%s, explanation_model=%s,
               explanation_status=%s where id=%s""",
            (exp.text, exp.model, exp.status, signal_id),
        )


def scan(conn: psycopg.Connection, run_id: int, now: datetime | None = None) -> tuple[int, int]:
    """Scan alle instrumenten. Geeft (aantal beoordeeld, aantal TRADE) terug."""
    now = now or utcnow()
    instruments = load_instruments()
    costs = load_costs()
    ids = db.ensure_instruments(conn, instruments)
    scanned = trades = 0
    for ins in instruments:
        for interval in ins.intervals:
            status = db.data_status_source(conn, ids[ins.symbol], interval) or ins.source
            src = get_source(status)
            window = db.recent_window(
                conn, ids[ins.symbol], interval, now - WINDOW * interval_delta(interval)
            )
            if window.empty:
                continue
            window["open_time"] = pd.to_datetime(window["open_time"], utc=True)
            rep = assess(
                window, interval, now, continuous=src.continuous, nominal_delay=src.nominal_delay
            )
            last = window["open_time"].iloc[-1].to_pydatetime()
            delay_s = int((now - (last + interval_delta(interval))).total_seconds())
            ctx = trend_pullback.Context(
                ins.symbol, interval, src.name, max(delay_s, 0), costs[src.name]
            )
            gate = freshness_gate(rep)
            if not gate.ok:
                sig = trend_pullback.no_trade(ctx, window, f"geen analyse: {gate.reason}")
            else:
                sig = trend_pullback.evaluate(window, ctx)
            if ins.experimental and sig.decision == "TRADE":
                sig.assumptions.append("Experimentele databron: alleen ter informatie.")
            signal_id = _insert_signal(conn, ids[ins.symbol], run_id, sig)
            conn.commit()
            scanned += 1
            if sig.decision == "TRADE":
                trades += 1
                if signal_id is not None:
                    _save_explanation(conn, signal_id, sig)
                    conn.commit()
            log.info(
                "scan %s %s: %s %s",
                ins.symbol,
                interval,
                sig.decision,
                sig.no_trade_reason or f"R/R {sig.rr_ratio:.2f} {sig.strength}",
            )
    return scanned, trades


def run_scan(trigger: str = "schedule", run_id: int | None = None) -> int:
    """Maak (of claim) een scan-run, voer hem uit en leg de uitkomst vast."""
    with db.connect() as conn:
        if run_id is None:
            run_id = db.create_scan_run(conn, trigger)
        db.start_scan_run(conn, run_id)
        conn.commit()
        try:
            scanned, trades = scan(conn, run_id)
            db.finish_scan_run(conn, run_id, scanned, trades, None)
        except Exception as exc:
            conn.rollback()
            log.exception("scan-run %s faalde", run_id)
            db.finish_scan_run(conn, run_id, None, None, str(exc)[:500])
        conn.commit()
    return run_id


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    run_scan("manual")
