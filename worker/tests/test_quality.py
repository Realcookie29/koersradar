from datetime import timedelta

from koersradar.ingest.quality import assess, find_gaps
from tests.conftest import make_candles


def _fresh(now, n=20):
    # laatste gesloten 15m-candle opende om 11:45 (sluit 12:00), now = 12:01
    last_open = now.replace(minute=45, hour=11)
    return make_candles(last_open - (n - 1) * timedelta(minutes=15), n)


def test_ok_when_fresh_and_complete(now):
    rep = assess(_fresh(now), "15m", now, continuous=True)
    assert rep.status == "ok", rep.detail


def test_gap_detected(now):
    df = _fresh(now).drop(index=5).reset_index(drop=True)
    assert len(find_gaps(df, "15m")) == 1
    assert assess(df, "15m", now, continuous=True).status == "gap"


def test_gaps_ignored_for_exchange_with_opening_hours(now):
    df = _fresh(now).drop(index=5).reset_index(drop=True)
    assert assess(df, "15m", now, continuous=False).status == "ok"


def test_delayed_then_stale(now):
    df = _fresh(now)
    assert assess(df, "15m", now + timedelta(minutes=25), continuous=True).status == "delayed"
    assert assess(df, "15m", now + timedelta(hours=1), continuous=True).status == "stale"


def test_nominal_delay_is_tolerated(now):
    df = _fresh(now)
    later = now + timedelta(minutes=20)
    assert assess(df, "15m", later, continuous=True).status == "delayed"
    assert (
        assess(df, "15m", later, continuous=True, nominal_delay=timedelta(minutes=15)).status
        == "ok"
    )


def test_empty_is_error(now):
    assert assess(_fresh(now).iloc[0:0], "15m", now, continuous=True).status == "error"
