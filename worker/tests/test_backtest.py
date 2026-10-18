from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from koersradar.backtest.engine import SimResult, Trade, simulate
from koersradar.backtest.metrics import buy_and_hold, random_entry, summarize
from koersradar.backtest.run import make_periods
from koersradar.config import CostModel
from koersradar.strategies import trend_pullback as tp

COSTS = CostModel(
    taker_fee=0.001,
    spread=0.0002,
    slippage_pct=0.0005,
    slippage_atr_frac=0.05,
    min_quote_volume_24h=0,
    checked_on=None,
)
FREE = CostModel(0.0, 0.0, 0.0, 0.0, 0.0, None)
T0 = datetime(2024, 1, 1, tzinfo=UTC)


def random_market(n: int, seed: int) -> pd.DataFrame:
    """Koersreeks met afwisselend stijgende en dalende fases, zodat er signalen ontstaan."""
    rng = np.random.default_rng(seed)
    drift = np.repeat(rng.choice([0.004, -0.002, 0.002], size=n // 60 + 1), 60)[:n]
    close = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.012, n)))
    opn = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {
            "open_time": pd.to_datetime([T0 + timedelta(hours=i) for i in range(n)], utc=True),
            "open": opn,
            "high": np.maximum(opn, close) * (1 + rng.uniform(0.001, 0.01, n)),
            "low": np.minimum(opn, close) * (1 - rng.uniform(0.001, 0.01, n)),
            "close": close,
            "volume": rng.uniform(50, 150, n),
        }
    )


def bars(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """Handgemaakte candles (open, high, low, close), één per uur."""
    o, h, low, c = zip(*rows, strict=True)
    n = len(rows)
    return pd.DataFrame(
        {
            "open_time": pd.to_datetime([T0 + timedelta(hours=i) for i in range(n)], utc=True),
            "open": o,
            "high": h,
            "low": low,
            "close": c,
            "volume": [1.0] * n,
        }
    )


def signals(n: int, at: int, stop: float, target: float, trend_ok: list[bool] | None = None):
    trade = [False] * n
    trade[at] = True
    return pd.DataFrame(
        {
            "trade": trade,
            "stop": [stop] * n,
            "target": [target] * n,
            "atr": [1.0] * n,
            "trend_ok": trend_ok or [True] * n,
        }
    )


# ---------- strategie: backtest en scanner nemen dezelfde beslissingen ----------


@pytest.mark.parametrize("seed", [2, 13, 1])  # 2 en 13 geven signalen, 1 juist niet
def test_evaluate_all_matches_evaluate(seed):
    df = random_market(420, seed)
    sig = tp.evaluate_all(df, COSTS)
    ctx = tp.Context("X/USDT", "1h", "binance", 0, COSTS)
    trades_seen = 0
    for t in range(tp.MIN_HISTORY - 2, len(df)):
        one = tp.evaluate(df.iloc[: t + 1], ctx)
        assert bool(sig["trade"].iloc[t]) == (one.decision == "TRADE"), (t, one.no_trade_reason)
        if one.decision == "TRADE":
            trades_seen += 1
            assert sig["stop"].iloc[t] == pytest.approx(one.stop_loss)
            assert sig["target"].iloc[t] == pytest.approx(one.target)
    assert trades_seen == int(sig["trade"].sum())
    assert (trades_seen > 0) == (seed != 1)


# ---------- uitvoering ----------


def test_target_hit_after_entry_on_next_open():
    df = bars([(100, 100, 100, 100), (100, 111, 99, 108), (108, 108, 108, 108)])
    res = simulate(df, signals(3, 0, 95, 110), FREE)
    [t] = res.trades
    assert t.entry_time == df["open_time"][1] and t.entry_price == 100
    assert t.exit_reason == "doel" and t.exit_price == 110
    assert t.r_multiple == pytest.approx(2.0)


def test_stop_wins_when_candle_hits_both():
    df = bars([(100, 100, 100, 100), (100, 111, 94, 100), (100, 100, 100, 100)])
    [t] = simulate(df, signals(3, 0, 95, 110), FREE).trades
    assert t.exit_reason == "stop" and t.r_multiple == pytest.approx(-1.0)


def test_gap_down_through_stop_fills_at_open():
    df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (90, 91, 89, 90)])
    [t] = simulate(df, signals(3, 0, 95, 110), FREE).trades
    assert t.exit_reason == "stop" and t.exit_price == 90
    assert t.r_multiple == pytest.approx(-2.0)


def test_skip_when_next_open_is_already_below_stop():
    df = bars([(100, 100, 100, 100), (94, 95, 93, 94), (94, 94, 94, 94)])
    res = simulate(df, signals(3, 0, 95, 110), FREE)
    assert res.trades == [] and res.skipped_gaps == 1


def test_trend_break_exits_on_next_open():
    df = bars([(100, 100, 100, 100), (100, 102, 99, 101), (103, 104, 102, 103)])
    res = simulate(df, signals(3, 0, 95, 110, trend_ok=[True, False, False]), FREE)
    [t] = res.trades
    assert t.exit_reason == "ongeldig" and t.exit_price == 103


def test_open_position_closes_at_end_of_period():
    df = bars([(100, 100, 100, 100), (100, 102, 99, 101), (101, 103, 100, 102)])
    [t] = simulate(df, signals(3, 0, 95, 110), FREE).trades
    assert t.exit_reason == "einde" and t.exit_price == 102


def test_costs_lower_the_result():
    df = bars([(100, 100, 100, 100), (100, 111, 99, 108), (108, 108, 108, 108)])
    [free] = simulate(df, signals(3, 0, 95, 110), FREE).trades
    [paid] = simulate(df, signals(3, 0, 95, 110), COSTS).trades
    assert paid.r_multiple < free.r_multiple
    assert paid.entry_price > 100 and paid.exit_price < 110


def test_no_new_entry_while_in_position():
    df = bars([(100, 100, 100, 100)] + [(100, 101, 99, 100)] * 4)
    sig = signals(5, 0, 95, 110)
    sig.loc[1, "trade"] = sig.loc[2, "trade"] = True
    [t] = simulate(df, sig, FREE).trades
    assert t.exit_reason == "einde"


def test_backtest_does_not_look_ahead():
    """Trades die al afgesloten waren op moment T veranderen niet als de data na T verandert."""
    df = random_market(900, 3)
    cut = 650
    altered = df.copy()
    altered.loc[cut:, ["open", "high", "low", "close"]] *= 0.5  # crash na T
    full = simulate(altered, tp.evaluate_all(altered, COSTS), COSTS).trades
    part = simulate(df.iloc[:cut], tp.evaluate_all(df.iloc[:cut], COSTS), COSTS).trades
    closed = [t for t in part if t.exit_reason != "einde"]
    assert closed, "testreeks moet afgesloten trades hebben"
    assert full[: len(closed)] == closed


# ---------- metrieken en periodes ----------


def _trade(r: float) -> Trade:
    ts = pd.Timestamp(T0)
    return Trade(ts, ts, 100, 95, 110, ts, 100, "doel" if r > 0 else "stop", r, r / 20, 1)


def test_summary_metrics():
    res = SimResult([_trade(r) for r in (2, -1, -1, 2)], bars=100, bars_in_trade=10, skipped_gaps=0)
    m = summarize(res, risk_frac=0.01)
    assert m["trades"] == 4 and m["winrate"] == 0.5 and m["avg_r"] == 0.5
    assert m["profit_factor"] == pytest.approx(2.0)
    assert m["return_pct"] == pytest.approx(1.02 * 0.99 * 0.99 * 1.02 - 1)
    assert m["max_drawdown_pct"] == pytest.approx(0.99 * 0.99 - 1)
    assert m["exposure"] == 0.1 and m["exit_doel"] == 2 and m["exit_stop"] == 2


def test_buy_and_hold_includes_costs():
    df = bars([(100, 100, 100, 100), (100, 120, 100, 120)])
    assert buy_and_hold(df, FREE, 0, 2, 1.0)["return_pct"] == pytest.approx(0.2)
    assert buy_and_hold(df, COSTS, 0, 2, 1.0)["return_pct"] < 0.2


def test_random_entry_is_reproducible():
    df = random_market(600, 5)
    sig = tp.evaluate_all(df, COSTS)
    a = random_entry(df, sig, COSTS, 0, len(df), 10, tp.MIN_HISTORY, runs=20)
    b = random_entry(df, sig, COSTS, 0, len(df), 10, tp.MIN_HISTORY, runs=20)
    assert a is not None and b is not None
    assert a["avg_r_median"] == b["avg_r_median"]


def test_periods_keep_holdout_out_by_default():
    ts = lambda s: pd.Timestamp(s, tz=UTC)  # noqa: E731
    args = dict(split=ts("2025-01-01"), holdout=ts("2026-01-01"), wf_months=6)
    periods = make_periods(ts("2024-01-01"), ts("2026-06-01"), include_holdout=False, **args)
    kinds = [p.kind for p in periods]
    assert kinds.count("train") == 1 and kinds.count("test") == 1 and "holdout" not in kinds
    assert all(p.end <= ts("2026-01-01") for p in periods)
    assert kinds.count("walk_forward") == 4
    with_holdout = make_periods(ts("2024-01-01"), ts("2026-06-01"), include_holdout=True, **args)
    assert with_holdout[-1].kind == "holdout"


def test_walk_forward_blocks_follow_calendar_quarters():
    ts = lambda s: pd.Timestamp(s, tz=UTC)  # noqa: E731
    periods = make_periods(
        ts("2023-12-31 20:00"),
        ts("2026-06-01"),
        split=ts("2025-01-01"),
        holdout=ts("2026-01-01"),
        wf_months=3,
        include_holdout=False,
    )
    blocks = [p for p in periods if p.kind == "walk_forward"]
    assert blocks[0].start == ts("2024-01-01") and blocks[-1].end == ts("2026-01-01")
    assert all(p.start.month in (1, 4, 7, 10) and p.start.day == 1 for p in blocks)
    assert len(blocks) == 8


def test_daily_trend_filter_does_not_look_ahead():
    """De dagtrend op uur t verandert niet als de koersen na t veranderen."""
    df = random_market(24 * 260, 4)
    cut = 24 * 230 + 7  # midden op een dag
    altered = df.copy()
    altered.loc[cut:, ["open", "high", "low", "close"]] *= 3.0
    full = tp.htf_trend(altered, "1D")
    part = tp.htf_trend(df.iloc[:cut], "1D")
    assert full.iloc[:cut].equals(part)
    assert part.any(), "testreeks moet een opwaartse dagtrend hebben"


def test_base_variant_equals_live_rules():
    df = random_market(420, 2)
    pd.testing.assert_frame_equal(
        tp.evaluate_all(df, COSTS), tp.evaluate_all(df, COSTS, tp.Variant())
    )
