from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

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
CTX = tp.Context("BTC/USDT", "1h", "binance", 60, COSTS)
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def frame(close: np.ndarray, volume: np.ndarray | None = None) -> pd.DataFrame:
    n = len(close)
    opn = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {
            "open_time": pd.to_datetime([T0 + timedelta(hours=i) for i in range(n)], utc=True),
            "open": opn,
            "high": np.maximum(opn, close) * 1.012,
            "low": np.minimum(opn, close) * 0.988,
            "close": close,
            "volume": volume if volume is not None else np.full(n, 100.0),
        }
    )


def uptrend_with_pullback() -> pd.DataFrame:
    up = 100 * np.exp(np.linspace(0, 0.5, 260))  # gestage stijging
    pull = up[-1] * np.exp(np.linspace(0, -0.04, 8)[1:])  # korte terugval -> RSI omlaag
    bounce = np.array([pull[-1] * 1.004])  # groene keer-candle
    close = np.r_[up, pull, bounce]
    vol = np.full(len(close), 100.0)
    vol[-1] = 180.0
    return frame(close, vol)


def test_trade_on_pullback_in_uptrend():
    sig = tp.evaluate(uptrend_with_pullback(), CTX)
    assert sig.decision == "TRADE", sig.no_trade_reason
    assert sig.stop_loss < sig.entry < sig.target
    assert sig.rr_ratio is not None and sig.rr_ratio >= tp.MIN_RR
    assert any("gebacktest" in a for a in sig.assumptions)


def test_no_trade_in_downtrend():
    close = 100 * np.exp(np.linspace(0, -0.5, 300))
    sig = tp.evaluate(frame(close), CTX)
    assert sig.decision == "NO_TRADE" and "trend" in sig.no_trade_reason


def test_no_trade_without_history():
    sig = tp.evaluate(frame(np.linspace(100, 110, 50)), CTX)
    assert sig.decision == "NO_TRADE" and "historie" in sig.no_trade_reason


def test_no_trade_when_illiquid():
    ctx = tp.Context(
        "X/USDT", "1h", "binance", 60, CostModel(**{**COSTS.__dict__, "min_quote_volume_24h": 1e12})
    )
    sig = tp.evaluate(uptrend_with_pullback(), ctx)
    assert sig.decision == "NO_TRADE" and not sig.liquidity_ok


def test_decision_uses_only_past_candles():
    """Het oordeel over candle t verandert niet door candles na t."""
    df = uptrend_with_pullback()
    extended = pd.concat(
        [
            df,
            frame(np.full(20, 1.0)).assign(
                open_time=lambda d: (
                    d["open_time"] + (df["open_time"].iloc[-1] - T0) + timedelta(hours=1)
                )
            ),
        ],
        ignore_index=True,
    )
    assert tp.evaluate(extended.iloc[: len(df)], CTX) == tp.evaluate(df, CTX)


def test_costs_can_veto_quiet_markets():
    """Bij heel rustige candles eten fees+spread het rendement op: dan geen trade."""
    df = uptrend_with_pullback()
    mid = (df["high"] + df["low"]) / 2
    df["high"], df["low"] = mid * 1.001, mid * 0.999
    sig = tp.evaluate(df, CTX)
    assert sig.decision == "NO_TRADE" and "risico/rendement" in sig.no_trade_reason
