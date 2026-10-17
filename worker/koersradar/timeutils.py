"""Tijd en intervallen. Alles in de worker is UTC en timezone-aware."""

from datetime import UTC, datetime, timedelta

INTERVALS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
}


def interval_delta(interval: str) -> timedelta:
    try:
        return INTERVALS[interval]
    except KeyError:
        raise ValueError(f"Onbekend interval: {interval!r}") from None


def utcnow() -> datetime:
    return datetime.now(UTC)
