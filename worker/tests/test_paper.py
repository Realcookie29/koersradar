from datetime import UTC, datetime

import pandas as pd
import pytest

from koersradar.backtest.engine import sell_proceeds, simulate
from koersradar.paper import ledger
from koersradar.strategies import trend_pullback as tp
from tests.test_backtest import COSTS, random_market


def _first_signal(df: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    sig = tp.evaluate_all(df, COSTS)
    rows = [i for i in range(len(df) - 30) if sig["trade"].iloc[i]]
    assert rows, "testdata zonder signaal"
    return rows[0], sig


def _replay(df: pd.DataFrame, i: int, sig: pd.DataFrame) -> ledger.Outcome:
    t = df["open_time"].iloc[i].to_pydatetime()
    return ledger.replay(df, t, float(sig["stop"].iloc[i]), float(sig["target"].iloc[i]), COSTS)


def test_replay_matches_backtest_engine():
    df = random_market(1600, seed=2)
    i, sig = _first_signal(df)
    only = sig.assign(trade=False)
    only.iloc[i, only.columns.get_loc("trade")] = True
    expected = simulate(df, only, COSTS, start=i).trades[0]
    out = _replay(df, i, sig)
    assert out.trade is not None
    assert out.trade.entry_time == expected.entry_time
    assert out.trade.exit_time == expected.exit_time
    assert out.trade.exit_reason == expected.exit_reason
    assert out.trade.r_multiple == pytest.approx(expected.r_multiple)
    assert out.trade.entry_raw == df["open"].iloc[i + 1]


def test_waits_for_next_candle_and_does_not_look_ahead():
    df = random_market(1600, seed=2)
    i, sig = _first_signal(df)
    assert _replay(df.iloc[: i + 1], i, sig).status == "wacht"
    full = _replay(df, i, sig)
    assert full.status == "gesloten" and full.trade is not None
    exit_row = int(df.index[df["open_time"] == full.trade.exit_time][0])
    if exit_row > i + 1:
        part = _replay(df.iloc[:exit_row], i, sig)
        assert part.status == "open"
        assert part.trade is not None and part.trade.entry_time == full.trade.entry_time


def test_missing_signal_candle_is_skipped():
    df = random_market(400, seed=2)
    out = ledger.replay(df, datetime(2030, 1, 1, tzinfo=UTC), 90.0, 120.0, COSTS)
    assert out.status == "overgeslagen"


def test_position_risks_one_percent_after_costs():
    df = random_market(1600, seed=2)
    i, sig = _first_signal(df)
    out = _replay(df, i, sig)
    assert out.trade is not None
    size, risk = ledger.position_size(out.trade, out.atr, COSTS, 10_000)
    assert risk == pytest.approx(100)
    loss = size * (out.trade.entry_price - sell_proceeds(out.trade.stop, out.atr, COSTS))
    assert loss == pytest.approx(100)


def test_risk_rules_block_new_trades():
    assert ledger.block_reason(1, set(), 10_000, 0) is None
    assert "al een positie" in (ledger.block_reason(1, {1}, 10_000, 0) or "")
    assert "posities open" in (ledger.block_reason(9, {1, 2, 3, 4, 5}, 10_000, 0) or "")
    assert ledger.block_reason(1, set(), 9_710, -290) is None  # 2,9% verlies: mag nog
    assert "dagverlies" in (ledger.block_reason(1, set(), 9_700, -300) or "")


def test_day_starts_at_midnight_in_amsterdam():
    start = ledger.day_start(datetime(2026, 10, 19, 21, 30, tzinfo=UTC))  # 23:30 in Amsterdam
    assert start == datetime(2026, 10, 18, 22, 0, tzinfo=UTC)
