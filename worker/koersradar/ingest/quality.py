"""Datakwaliteit: gaten, duplicaten en versheid van een candle-venster."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from koersradar.timeutils import interval_delta


@dataclass
class QualityReport:
    status: str  # ok | delayed | stale | gap | error
    last_candle_at: datetime | None
    gaps: list[datetime] = field(default_factory=list)
    duplicates: int = 0
    detail: str | None = None


def find_gaps(df: pd.DataFrame, interval: str) -> list[datetime]:
    """Ontbrekende open_times in een doorlopende (24/7) reeks."""
    if len(df) < 2:
        return []
    times = pd.DatetimeIndex(df["open_time"])
    expected = pd.date_range(times[0], times[-1], freq=interval_delta(interval))
    return [t.to_pydatetime() for t in expected.difference(times)]


def assess(
    df: pd.DataFrame,
    interval: str,
    now: datetime,
    *,
    continuous: bool,
    nominal_delay: timedelta = timedelta(0),
    tolerance: timedelta = timedelta(minutes=5),
    stale_after: timedelta | None = None,
) -> QualityReport:
    """Beoordeel een venster GESLOTEN candles.

    - gap:     ontbrekende candles (alleen bij 24/7-markten te bepalen)
    - delayed: laatste candle later dan verwacht, maar binnen stale_after
    - stale:   te oud om op te handelen
    Voor niet-doorlopende markten (beurs) is 'stale' buiten openingstijden normaal;
    de signal engine behandelt dat als NO_TRADE ("markt gesloten / data verouderd").
    """
    if df.empty:
        return QualityReport(status="error", last_candle_at=None, detail="geen data")

    dupes = int(df["open_time"].duplicated().sum())
    last = df["open_time"].iloc[-1].to_pydatetime()
    step = interval_delta(interval)
    stale_after = stale_after or 3 * step

    # Verwacht: laatste gesloten candle opende op (now - step - delay), afgerond.
    age = now - (last + step)  # tijd sinds sluiten laatste candle
    gaps = find_gaps(df, interval) if continuous else []

    if dupes:
        status, detail = "error", f"{dupes} dubbele candles"
    elif gaps:
        status, detail = "gap", f"{len(gaps)} ontbrekende candles"
    elif age > stale_after + nominal_delay:
        status, detail = "stale", f"laatste candle {age} oud"
    elif age > step + nominal_delay + tolerance:
        status, detail = "delayed", f"laatste candle {age} oud"
    else:
        status, detail = "ok", None
    return QualityReport(
        status=status, last_candle_at=last, gaps=gaps, duplicates=dupes, detail=detail
    )
