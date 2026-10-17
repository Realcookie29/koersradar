"""Eén ingest-ronde: per instrument+interval nieuwe gesloten candles ophalen,
kwaliteit beoordelen, opslaan (Postgres-venster + Parquet) en data_status bijwerken."""

import logging
from datetime import datetime, timedelta

import pandas as pd

from koersradar import db
from koersradar.config import Instrument, load_instruments
from koersradar.ingest.fetch import fetch_range, fetch_with_fallback
from koersradar.ingest.quality import QualityReport, assess
from koersradar.ingest.store import append_history
from koersradar.sources.base import DataSource
from koersradar.sources.registry import get_source
from koersradar.timeutils import interval_delta, utcnow

log = logging.getLogger(__name__)

# Venster waarover kwaliteit wordt beoordeeld (en dat de engine later gebruikt).
QUALITY_WINDOW = 250


def _assess_window(
    conn, instrument_id: int, interval: str, now: datetime, src: DataSource
) -> QualityReport:
    step = interval_delta(interval)
    window = db.recent_window(conn, instrument_id, interval, now - QUALITY_WINDOW * step)
    if not window.empty:
        window["open_time"] = pd.to_datetime(window["open_time"], utc=True)
    return assess(window, interval, now, continuous=src.continuous, nominal_delay=src.nominal_delay)


def ingest_instrument(
    conn,
    ins: Instrument,
    instrument_id: int,
    interval: str,
    now: datetime,
    initial_days: int = 7,
) -> QualityReport:
    step = interval_delta(interval)
    last = db.last_candle_time(conn, instrument_id, interval)
    since = (last + step) if last else now - timedelta(days=initial_days)

    primary = get_source(ins.source)
    fallback = get_source(ins.fallback) if ins.fallback else None
    try:
        outcome = fetch_with_fallback(primary, fallback, ins.symbol, interval, since, now)
    except Exception as exc:
        rep = QualityReport(status="error", last_candle_at=last, detail=str(exc)[:200])
        db.upsert_status(conn, instrument_id, interval, ins.source, rep)
        return rep

    src = outcome.source
    db.upsert_candles(conn, instrument_id, interval, src.name, outcome.candles)
    if not outcome.candles.empty:
        append_history(src.name, ins.symbol, interval, outcome.candles)

    rep = _assess_window(conn, instrument_id, interval, now, src)
    if rep.gaps:
        # Gaten herstellen: vanaf het eerste ontbrekende tijdstip opnieuw ophalen.
        try:
            repair = fetch_range(src, ins.symbol, interval, min(rep.gaps), now)
            db.upsert_candles(conn, instrument_id, interval, src.name, repair)
            rep = _assess_window(conn, instrument_id, interval, now, src)
        except Exception as exc:
            log.warning("gap-herstel faalde voor %s %s: %s", ins.symbol, interval, exc)
    if outcome.used_fallback:
        rep.detail = f"fallback {src.name}" + (f"; {rep.detail}" if rep.detail else "")
    db.upsert_status(conn, instrument_id, interval, src.name, rep)
    return rep


def ingest_once(now: datetime | None = None) -> dict[str, str]:
    now = now or utcnow()
    instruments = load_instruments()
    results: dict[str, str] = {}
    with db.connect() as conn:
        ids = db.ensure_instruments(conn, instruments)
        for ins in instruments:
            for interval in ins.intervals:
                rep = ingest_instrument(conn, ins, ids[ins.symbol], interval, now)
                conn.commit()
                results[f"{ins.symbol} {interval}"] = rep.status
                log.info("%s %s: %s %s", ins.symbol, interval, rep.status, rep.detail or "")
        db.prune(conn, now)
        conn.commit()
    return results


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    for key, status in ingest_once().items():
        print(f"{status:8} {key}")
