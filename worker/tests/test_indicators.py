import numpy as np
import pandas as pd
import pytest

from koersradar.indicators.core import atr, ema, rsi, sma


def _ohlc(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    high = close * (1 + rng.uniform(0, 0.01, n))
    low = close * (1 - rng.uniform(0, 0.01, n))
    return pd.DataFrame({"close": close, "high": high, "low": low})


def test_ema_constant_series():
    s = pd.Series([5.0] * 60)
    assert ema(s, 50).dropna().eq(5.0).all()


def test_rsi_only_rising_is_100():
    s = pd.Series(np.arange(1.0, 40.0))
    assert rsi(s).dropna().eq(100.0).all()


def test_no_lookahead():
    """Waarden tot t mogen niet veranderen als er toekomstige candles bijkomen."""
    df = _ohlc()
    cut = 300
    for f in (
        lambda d: ema(d["close"], 50),
        lambda d: rsi(d["close"]),
        lambda d: atr(d["high"], d["low"], d["close"]),
        lambda d: sma(d["close"], 20),
    ):
        full = f(df).iloc[:cut]
        partial = f(df.iloc[:cut])
        pd.testing.assert_series_equal(full, partial)


def test_matches_talib():
    talib = pytest.importorskip("talib")
    df = _ohlc()
    c, h, low = df["close"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    np.testing.assert_allclose(ema(df["close"], 50), talib.EMA(c, 50), rtol=1e-9, equal_nan=True)
    np.testing.assert_allclose(rsi(df["close"]), talib.RSI(c, 14), rtol=1e-9, equal_nan=True)
    np.testing.assert_allclose(
        atr(df["high"], df["low"], df["close"]),
        talib.ATR(h, low, c, 14),
        rtol=1e-9,
        equal_nan=True,
    )
