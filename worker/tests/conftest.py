from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from koersradar.sources.base import normalize
from koersradar.timeutils import interval_delta

NOW = datetime(2026, 10, 17, 12, 1, tzinfo=UTC)


def make_candles(start: datetime, n: int, interval: str = "15m") -> pd.DataFrame:
    step = interval_delta(interval)
    times = [start + i * step for i in range(n)]
    return normalize(
        pd.DataFrame(
            {
                "open_time": times,
                "open": [100.0 + i for i in range(n)],
                "high": [101.0 + i for i in range(n)],
                "low": [99.0 + i for i in range(n)],
                "close": [100.5 + i for i in range(n)],
                "volume": [10.0] * n,
            }
        )
    )


class FakeSource:
    """In-memory DataSource voor tests; kan falen op commando."""

    continuous = True
    nominal_delay = timedelta(0)

    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        fail: bool = False,
        limit: int = 1000,
        short_pages: bool = False,
    ):
        self.name, self.data, self.fail, self._limit = name, data, fail, limit
        self.short_pages = short_pages  # zoals Coinbase: geeft limit-1 candles terug
        self.calls = 0

    def fetch_ohlcv(self, symbol, interval, since, limit):
        self.calls += 1
        if self.fail:
            raise ConnectionError("simulated outage")
        df = self.data[self.data["open_time"] >= pd.Timestamp(since)] if since else self.data
        return df.head(limit - 1 if self.short_pages else limit).reset_index(drop=True)

    def max_limit(self) -> int:
        return self._limit


@pytest.fixture
def now() -> datetime:
    return NOW
