"""Nieuwe instapideeën, alleen voor onderzoek in backtests (zie docs/nieuwe-instap.md).

Elke functie geeft per candle dezelfde kolommen als `trend_pullback.evaluate_all`, zodat
`backtest.engine.simulate` ze kan naspelen: `trade`, `stop`, `target`, `atr` en `trend_ok`.
Hier betekent `trend_ok` "positie aanhouden"; is die False, dan uit op de volgende open.
Er is geen vast doel (target = oneindig): een winnaar loopt door tot de uitstapregel.

Rij t gebruikt alleen candles <= t. Tests bewaken dat er niet vooruit wordt gekeken.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from koersradar.config import CostModel
from koersradar.indicators.core import atr, ema, rsi, sma

MIN_HISTORY = 210
BREAKOUT_H = 24
EXIT_H = 12
QUIET_DAYS = 30
MOMENTUM_DAYS = 7
MOMENTUM_TOP = 3
MOMENTUM_KEEP = 5


def bars_per_hour(df: pd.DataFrame) -> int:
    step = pd.DatetimeIndex(df["open_time"]).to_series().diff().median()
    return max(1, int(pd.Timedelta(hours=1) / step))


def _base(df: pd.DataFrame, costs: CostModel) -> pd.Series:
    """Genoeg historie en genoeg omzet in de laatste 24 uur (zelfde filter als trend-pullback)."""
    qv24 = (
        (df["close"] * df["volume"])
        .set_axis(pd.DatetimeIndex(df["open_time"]))
        .rolling("24h")
        .sum()
        .to_numpy()
    )
    enough = np.arange(len(df)) >= MIN_HISTORY - 1
    return pd.Series(enough & (qv24 >= costs.min_quote_volume_24h), index=df.index)


def _frame(trade: pd.Series, stop: pd.Series, a: pd.Series, keep: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade": trade.fillna(False).astype(bool),
            "stop": stop,
            "target": np.inf,
            "atr": a,
            "trend_ok": keep.fillna(False).astype(bool),
        },
        index=trade.index,
    )


def htf_series(df: pd.DataFrame, htf: str, fn: Callable[[pd.DataFrame], pd.Series]) -> pd.Series:
    """Waarde van `fn` op een hogere tijdschaal per candle van df, pas na sluiten van die candle."""
    times = pd.DatetimeIndex(df["open_time"])
    step = times.to_series().diff().median()
    big = (
        df.set_axis(times)[["open", "high", "low", "close"]]
        .resample(htf, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    values = fn(big)
    available = pd.DataFrame(
        {
            "at": (pd.DatetimeIndex(big.index) + pd.Timedelta(htf)).as_unit("ns"),
            "v": values.to_numpy(dtype=float),
        }
    )
    now = pd.DataFrame({"at": (times + step).as_unit("ns")})
    merged = pd.merge_asof(now, available, on="at", direction="backward")
    return pd.Series(merged["v"].to_numpy(), index=df.index)


def breakout(df: pd.DataFrame, costs: CostModel, quiet: bool = False) -> pd.DataFrame:
    """Slot boven de hoogste high van de vorige 24 uur, in een markt boven EMA 200."""
    h = bars_per_hour(df)
    close, high, low = df["close"], df["high"], df["low"]
    a = atr(high, low, close)
    prev_high = high.shift(1).rolling(BREAKOUT_H * h).max()
    prev_low = low.shift(1).rolling(BREAKOUT_H * h).min()
    trade = _base(df, costs) & (close > prev_high) & (close > ema(close, 200))
    if quiet:
        width = (prev_high - prev_low) / close
        normal = width.shift(1).rolling(QUIET_DAYS * 24 * h, min_periods=10 * 24 * h).median()
        trade &= width < normal
    keep = close >= low.shift(1).rolling(EXIT_H * h).min()
    return _frame(trade, close - 2 * a, a, keep)


def breakout_quiet(df: pd.DataFrame, costs: CostModel) -> pd.DataFrame:
    return breakout(df, costs, quiet=True)


def pullback_rsi2(df: pd.DataFrame, costs: CostModel) -> pd.DataFrame:
    """Connors: korte dip (RSI 2 onder 10) in een markt boven EMA 200; uit boven SMA 5."""
    close, high, low = df["close"], df["high"], df["low"]
    a = atr(high, low, close)
    trade = _base(df, costs) & (close > ema(close, 200)) & (rsi(close, 2) < 10)
    keep = close <= sma(close, 5)
    return _frame(trade, close - 3 * a, a, keep)


def momentum_ranks(closes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Per munt: rendement over 7 dagen en de rang daarvan onder alle munten (1 = sterkste).

    Alleen tijdstippen waarop elke munt een candle heeft tellen mee; anders geen rang.
    """
    h = bars_per_hour(next(iter(closes.values())))
    lookback = MOMENTUM_DAYS * 24 * h
    ret = pd.DataFrame(
        {
            s: (d["close"] / d["close"].shift(lookback) - 1).set_axis(
                pd.DatetimeIndex(d["open_time"])
            )
            for s, d in closes.items()
        }
    )
    complete = ret.notna().all(axis=1)
    rank = ret.rank(axis=1, ascending=False).where(complete)
    out = {}
    for s, d in closes.items():
        t = pd.DatetimeIndex(d["open_time"])
        out[s] = pd.DataFrame(
            {"ret": ret[s].reindex(t).to_numpy(), "rank": rank[s].reindex(t).to_numpy()},
            index=d.index,
        )
    return out


def momentum(df: pd.DataFrame, costs: CostModel, ranks: pd.DataFrame) -> pd.DataFrame:
    """Koop een van de 3 sterkste munten (7 dagen); houd vast zolang hij in de top 5 blijft."""
    close = df["close"]
    a = atr(df["high"], df["low"], close)
    day_atr = htf_series(df, "1D", lambda d: atr(d["high"], d["low"], d["close"]))
    up = ranks["ret"] > 0
    trade = _base(df, costs) & (ranks["rank"] <= MOMENTUM_TOP) & up & day_atr.notna()
    keep = (ranks["rank"] <= MOMENTUM_KEEP) & up
    return _frame(trade, close - 2 * day_atr, a, keep)
