from datetime import timedelta

import pytest

from koersradar.ingest.fetch import fetch_range, fetch_with_fallback
from tests.conftest import FakeSource, make_candles


def test_paginates_and_returns_only_closed(now):
    start = now - timedelta(hours=10)
    data = make_candles(start.replace(minute=0), 45)  # loopt tot voorbij 'now'
    src = FakeSource("fake", data, limit=10)
    out = fetch_range(src, "BTC/USDT", "15m", start.replace(minute=0), now)
    assert src.calls > 1
    assert (out["open_time"] + timedelta(minutes=15) <= now).all()
    assert out["open_time"].is_unique


def test_short_pages_do_not_stop_pagination(now):
    start = (now - timedelta(hours=10)).replace(minute=0)
    data = make_candles(start, 40)
    src = FakeSource("coinbase", data, limit=10, short_pages=True)
    out = fetch_range(src, "BTC/USDT", "15m", start, now)
    expected_last = data["open_time"][data["open_time"] + timedelta(minutes=15) <= now].iloc[-1]
    assert out["open_time"].iloc[-1] == expected_last


def test_fallback_used_when_primary_fails(now):
    data = make_candles(now - timedelta(hours=3), 8)
    primary = FakeSource("binance", data, fail=True)
    backup = FakeSource("coinbase", data)
    out = fetch_with_fallback(primary, backup, "BTC/USDT", "15m", now - timedelta(hours=3), now)
    assert out.used_fallback and out.source.name == "coinbase" and not out.candles.empty


def test_failure_without_fallback_raises(now):
    primary = FakeSource("binance", make_candles(now, 1), fail=True)
    with pytest.raises(ConnectionError):
        fetch_with_fallback(primary, None, "BTC/USDT", "15m", now - timedelta(hours=1), now)


def test_empty_result_does_not_trigger_fallback(now):
    # Nog geen nieuwe gesloten candle sinds vorige ronde: geen reden voor fallback.
    primary = FakeSource("binance", make_candles(now - timedelta(hours=3), 8))
    backup = FakeSource("coinbase", make_candles(now - timedelta(hours=3), 8))
    out = fetch_with_fallback(primary, backup, "BTC/USDT", "15m", now, now)
    assert not out.used_fallback and out.candles.empty and backup.calls == 0
