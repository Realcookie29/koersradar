"""Gemeenschappelijke interface voor koersbronnen.

Elke adapter levert een DataFrame met kolommen OHLCV_COLUMNS, gesorteerd op
open_time (UTC, tz-aware). Nieuwe markt = nieuwe adapter die dit contract volgt.
"""

from datetime import datetime, timedelta
from typing import Protocol

import pandas as pd

from koersradar.timeutils import interval_delta

OHLCV_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]


class DataSource(Protocol):
    name: str
    # Typische vertraging van deze bron t.o.v. de markt (yfinance/Euronext ~15 min).
    nominal_delay: timedelta
    # True voor 24/7-markten (crypto): ontbrekende candles zijn dan echte gaten.
    continuous: bool

    def fetch_ohlcv(
        self, symbol: str, interval: str, since: datetime | None, limit: int
    ) -> pd.DataFrame: ...

    def max_limit(self) -> int:
        """Maximaal aantal candles per request."""
        ...


def empty_frame() -> pd.DataFrame:
    df = pd.DataFrame(columns=OHLCV_COLUMNS)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Forceer kolommen, UTC, sortering en verwijder exacte duplicaten."""
    if df.empty:
        return empty_frame()
    out = df[OHLCV_COLUMNS].copy()
    out["open_time"] = pd.to_datetime(out["open_time"], utc=True)
    for col in OHLCV_COLUMNS[1:]:
        out[col] = out[col].astype("float64")
    out = out.drop_duplicates(subset="open_time", keep="last")
    return out.sort_values("open_time").reset_index(drop=True)


def closed_only(df: pd.DataFrame, interval: str, now: datetime) -> pd.DataFrame:
    """Gooi de nog lopende candle weg. Een candle is gesloten als open_time + interval <= now.

    Signalen en opslag gebruiken uitsluitend gesloten candles (voorkomt look-ahead).
    """
    if df.empty:
        return df
    cutoff = pd.Timestamp(now) - interval_delta(interval)
    return df[df["open_time"] <= cutoff].reset_index(drop=True)
