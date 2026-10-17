"""Postgres-toegang voor de worker (service-verbinding, omzeilt RLS)."""

import os
from datetime import datetime, timedelta

import pandas as pd
import psycopg

from koersradar.config import Instrument
from koersradar.ingest.quality import QualityReport

# Hoeveel historie in Postgres blijft (rest staat in Parquet).
RETENTION = {"15m": timedelta(days=90), "1h": timedelta(days=730)}


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL ontbreekt (zie .env.example)")
    return psycopg.connect(url, autocommit=False)


def ensure_instruments(conn: psycopg.Connection, instruments: list[Instrument]) -> dict[str, int]:
    with conn.cursor() as cur:
        for ins in instruments:
            cur.execute(
                """insert into public.instruments (symbol, market, source, experimental)
                   values (%s, %s, %s, %s)
                   on conflict (symbol) do update
                   set source = excluded.source, experimental = excluded.experimental""",
                (ins.symbol, ins.market, ins.source, ins.experimental),
            )
        cur.execute("select symbol, id from public.instruments")
        ids = {sym: id_ for sym, id_ in cur.fetchall()}
    conn.commit()
    return ids


def last_candle_time(
    conn: psycopg.Connection, instrument_id: int, interval: str
) -> datetime | None:
    with conn.cursor() as cur:
        cur.execute(
            "select max(open_time) from public.candles where instrument_id=%s and interval=%s",
            (instrument_id, interval),
        )
        row = cur.fetchone()
    return row[0] if row else None


def recent_window(
    conn: psycopg.Connection, instrument_id: int, interval: str, since: datetime
) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(
            """select open_time, open, high, low, close, volume from public.candles
               where instrument_id=%s and interval=%s and open_time >= %s order by open_time""",
            (instrument_id, interval, since),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume"])


def upsert_candles(
    conn: psycopg.Connection, instrument_id: int, interval: str, source: str, df: pd.DataFrame
) -> None:
    if df.empty:
        return
    times = pd.to_datetime(df["open_time"], utc=True).dt.to_pydatetime()
    ohlcv = df[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float).tolist()
    rows = [
        (instrument_id, interval, t, *vals, source) for t, vals in zip(times, ohlcv, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """insert into public.candles
               (instrument_id, interval, open_time, open, high, low, close, volume, source)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               on conflict (instrument_id, interval, open_time) do update set
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume, source=excluded.source,
                 ingested_at=now()""",
            rows,
        )


def upsert_status(
    conn: psycopg.Connection, instrument_id: int, interval: str, source: str, rep: QualityReport
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """insert into public.data_status
               (instrument_id, interval, source, last_candle_at, last_checked_at, status, detail)
               values (%s,%s,%s,%s,now(),%s,%s)
               on conflict (instrument_id, interval) do update set
                 source=excluded.source, last_candle_at=excluded.last_candle_at,
                 last_checked_at=now(), status=excluded.status, detail=excluded.detail""",
            (instrument_id, interval, source, rep.last_candle_at, rep.status, rep.detail),
        )


def prune(conn: psycopg.Connection, now: datetime) -> None:
    with conn.cursor() as cur:
        for interval, keep in RETENTION.items():
            cur.execute(
                "delete from public.candles where interval=%s and open_time < %s",
                (interval, now - keep),
            )


def data_status_source(conn: psycopg.Connection, instrument_id: int, interval: str) -> str | None:
    """Bron waarmee de laatste data binnenkwam (kan de fallback zijn)."""
    with conn.cursor() as cur:
        cur.execute(
            "select source from public.data_status where instrument_id=%s and interval=%s",
            (instrument_id, interval),
        )
        row = cur.fetchone()
    return row[0] if row else None


def create_scan_run(conn: psycopg.Connection, trigger: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "insert into public.scan_runs (trigger, requested_by) values (%s, null) returning id",
            (trigger,),
        )
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def claim_pending_manual_run(conn: psycopg.Connection) -> int | None:
    """Pak de oudste openstaande handmatige aanvraag; dubbele aanvragen vallen samen."""
    with conn.cursor() as cur:
        cur.execute(
            """select id from public.scan_runs where status='pending'
               order by requested_at limit 1 for update skip locked"""
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """update public.scan_runs set status='done', finished_at=now(),
               error='samengevoegd met run ' || %s
               where status='pending' and id <> %s""",
            (row[0], row[0]),
        )
    return int(row[0])


def start_scan_run(conn: psycopg.Connection, run_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update public.scan_runs set status='running', started_at=now() where id=%s",
            (run_id,),
        )


def finish_scan_run(
    conn: psycopg.Connection,
    run_id: int,
    scanned: int | None,
    trades: int | None,
    error: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """update public.scan_runs set status=%s, finished_at=now(),
               instruments_scanned=%s, trade_count=%s, error=%s where id=%s""",
            ("error" if error else "done", scanned, trades, error, run_id),
        )


def prune_signals(conn: psycopg.Connection, now: datetime) -> None:
    """NO_TRADE-records na 14 dagen weg; TRADE-signalen blijven voor evaluatie."""
    with conn.cursor() as cur:
        cur.execute(
            """delete from public.signals where decision='NO_TRADE' and created_at < %s
               and id not in (select signal_id from public.paper_trades)""",
            (now - timedelta(days=14),),
        )
