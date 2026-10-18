import numpy as np
import pandas as pd
import pytest

from koersradar.backtest.engine import simulate
from koersradar.strategies import ideas
from tests.test_backtest import COSTS, random_market

SINGLE = {
    "breakout": ideas.breakout,
    "breakout-rust": ideas.breakout_quiet,
    "terugval": ideas.pullback_rsi2,
}


def _same(a: pd.DataFrame, b: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


@pytest.mark.parametrize("name", list(SINGLE))
def test_idea_does_not_look_ahead(name):
    df = random_market(1600, seed=2)
    full = SINGLE[name](df, COSTS)
    for cut in (400, 900, 1300):
        part = SINGLE[name](df.iloc[:cut], COSTS)
        _same(part, full.iloc[:cut])


@pytest.mark.parametrize("name", list(SINGLE))
def test_idea_produces_trades(name):
    df = random_market(1600, seed=2)
    sig = SINGLE[name](df, COSTS)
    assert sig["trade"].any()
    assert np.isinf(sig["target"]).all()
    assert len(simulate(df, sig, COSTS).trades) > 0


def test_breakout_needs_close_above_previous_day_high():
    df = random_market(1600, seed=2)
    sig = ideas.breakout(df, COSTS)
    prev_high = df["high"].shift(1).rolling(24).max()
    assert (df.loc[sig["trade"], "close"] > prev_high[sig["trade"]]).all()


def test_momentum_does_not_look_ahead():
    markets = {f"M{s}": random_market(1600, seed=s) for s in (1, 2, 13, 5)}
    full = ideas.momentum_ranks(markets)
    cut = 1000
    part = ideas.momentum_ranks({k: v.iloc[:cut] for k, v in markets.items()})
    for k in markets:
        _same(part[k], full[k].iloc[:cut])
        _same(
            ideas.momentum(markets[k].iloc[:cut], COSTS, part[k]),
            ideas.momentum(markets[k], COSTS, full[k]).iloc[:cut],
        )


def test_momentum_ranks_strongest_first():
    markets = {f"M{s}": random_market(400, seed=s) for s in (1, 2, 13)}
    r = ideas.momentum_ranks(markets)
    last = {k: v["ret"].iloc[-1] for k, v in r.items()}
    best = max(last, key=lambda k: last[k])
    assert r[best]["rank"].iloc[-1] == 1


def test_daily_values_wait_for_daily_close():
    df = random_market(24 * 40, seed=2)
    full = ideas.htf_series(df, "1D", lambda d: d["close"])
    # Tot en met het laatste uur van dag 1 is de slot van dag 1 nog niet bekend.
    assert full.iloc[:23].isna().all()
    assert full.iloc[23] == df["close"].iloc[23]


def test_resample_builds_only_closed_candles():
    df = random_market(24 * 3 + 5, seed=2)  # drie volle dagen en 5 uur van dag 4
    day = ideas.resample(df, "1D")
    assert len(day) == 3
    first = df.iloc[:24]
    row = day.iloc[0]
    assert row["open"] == first["open"].iloc[0]
    assert row["high"] == first["high"].max()
    assert row["low"] == first["low"].min()
    assert row["close"] == first["close"].iloc[-1]
    assert row["volume"] == pytest.approx(first["volume"].sum())
    assert len(ideas.resample(df.iloc[: 24 * 3], "1D")) == 3  # laatste dag net vol


def test_resample_does_not_look_ahead():
    df = random_market(24 * 30, seed=2)
    full = ideas.resample(df, "4h")
    part = ideas.resample(df.iloc[: 24 * 20 + 3], "4h")
    _same(part, full.iloc[: len(part)])


@pytest.mark.parametrize(("entry", "exit_"), [(20, 10), (55, 20)])
def test_turtle_does_not_look_ahead(entry, exit_):
    df = ideas.resample(random_market(24 * 200, seed=2), "4h")
    full = ideas.turtle(df, COSTS, entry, exit_)
    assert full["trade"].any()
    for cut in (150, 600):
        _same(ideas.turtle(df.iloc[:cut], COSTS, entry, exit_), full.iloc[:cut])
