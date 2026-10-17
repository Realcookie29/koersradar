"""Technische indicatoren in pandas — klein, controleerbaar en getest.

Elke waarde op rij t gebruikt alleen rijen <= t (geen look-ahead).
Definities volgen de gangbare (TA-Lib/Wilder) conventies.
"""

import pandas as pd


def ema(close: pd.Series, period: int) -> pd.Series:
    """EMA met SMA-seed over de eerste `period` waarden (zoals TA-Lib)."""
    out = pd.Series(float("nan"), index=close.index)
    if len(close) < period:
        return out
    k = 2 / (period + 1)
    prev = close.iloc[:period].mean()
    out.iloc[period - 1] = prev
    for i in range(period, len(close)):
        prev = close.iloc[i] * k + prev * (1 - k)
        out.iloc[i] = prev
    return out


def _wilder(values: pd.Series, period: int) -> pd.Series:
    """Wilder-smoothing: seed = gemiddelde van eerste `period`, daarna (prev*(n-1)+x)/n."""
    out = pd.Series(float("nan"), index=values.index)
    notna = values.notna().to_numpy()
    if notna.sum() < period:
        return out
    start = int(notna.argmax())  # positie van eerste geldige waarde
    prev = values.iloc[start : start + period].mean()
    out.iloc[start + period - 1] = prev
    for i in range(start + period, len(values)):
        prev = (prev * (period - 1) + values.iloc[i]) / period
        out.iloc[i] = prev
    return out


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = _wilder(delta.clip(lower=0), period)
    loss = _wilder((-delta).clip(lower=0), period)
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    return out.where(loss != 0, 100.0).where(gain.notna())


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(
        axis=1
    )
    tr.iloc[0] = float("nan")  # eerste TR heeft geen vorige close (TA-Lib-conventie)
    return _wilder(tr, period)


def sma(values: pd.Series, period: int) -> pd.Series:
    return values.rolling(period, min_periods=period).mean()
