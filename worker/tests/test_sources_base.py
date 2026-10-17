from datetime import timedelta

import pandas as pd

from koersradar.sources.base import closed_only, normalize
from tests.conftest import make_candles


def test_closed_only_drops_running_candle(now):
    # Laatste candle opent om 12:00 en loopt nog tot 12:15 -> moet weg.
    df = make_candles(now.replace(minute=0) - timedelta(minutes=45), 4)
    out = closed_only(df, "15m", now)
    assert out["open_time"].iloc[-1] == pd.Timestamp(now.replace(minute=0) - timedelta(minutes=15))
    assert len(out) == 3


def test_normalize_dedupes_and_sorts_utc(now):
    df = make_candles(now - timedelta(hours=2), 4)
    shuffled = pd.concat([df.iloc[::-1], df.iloc[[1]]])
    out = normalize(shuffled)
    assert len(out) == 4
    assert out["open_time"].is_monotonic_increasing
    assert str(out["open_time"].dt.tz) == "UTC"
