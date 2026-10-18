"""Baseline-strategie: koop een pullback in een opwaartse trend (alleen long).

Rollen (zie docs/plan.md):
  trend    EMA50 > EMA200 en slot > EMA200
  timing   RSI(14) dook recent onder 40 en draait nu omhoog
  volume   volume t.o.v. 20-periode gemiddelde (bevestiging, verhoogt sterkte)
  risico   stop = slot - 1,5 x ATR(14); doel = 2R
Werkt uitsluitend op GESLOTEN candles; instap = indicatief op de open van de volgende candle.

Deze strategie is nog NIET gebacktest (fase 3). Behandel uitkomsten als ongetest.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from koersradar.config import CostModel
from koersradar.indicators.core import atr, ema, rsi, sma
from koersradar.signals.model import CostAssumptions, Fact, Signal, rr_after_costs

VERSION = "trend-pullback-0.1"
MIN_HISTORY = 210
RSI_DIP = 40.0
RSI_MAX_ENTRY = 60.0
DIP_LOOKBACK = 6
STOP_ATR = 1.5
TARGET_R = 2.0
MIN_RR = 1.5

Strength = Literal["zwak", "matig", "sterk"]


@dataclass(frozen=True)
class Context:
    instrument: str
    interval: str
    data_source: str
    data_delay_s: int
    costs: CostModel


def _costs(c: CostModel) -> CostAssumptions:
    return CostAssumptions(taker_fee=c.taker_fee, spread=c.spread, slippage=c.slippage_pct)


def quote_volume_24h(df: pd.DataFrame) -> float:
    last = df["open_time"].iloc[-1]
    window = df[df["open_time"] > last - pd.Timedelta(hours=24)]
    return float((window["close"] * window["volume"]).sum())


def no_trade(
    ctx: Context,
    df: pd.DataFrame,
    reason: str,
    facts: list[Fact] | None = None,
    liquidity_ok: bool = True,
) -> Signal:
    return Signal(
        instrument=ctx.instrument,
        interval=ctx.interval,
        decision="NO_TRADE",
        no_trade_reason=reason,
        facts=facts or [],
        data_source=ctx.data_source,
        last_candle_at=df["open_time"].iloc[-1].to_pydatetime(),
        data_delay_s=ctx.data_delay_s,
        cost_assumptions=_costs(ctx.costs),
        liquidity_ok=liquidity_ok,
        strategy_version=VERSION,
    )


def evaluate(df: pd.DataFrame, ctx: Context) -> Signal:
    """Beoordeel de laatste gesloten candle. df: gesorteerd, alleen gesloten candles."""
    if len(df) < MIN_HISTORY:
        return no_trade(ctx, df, f"te weinig historie ({len(df)} van {MIN_HISTORY} candles)")

    close, high, low, opn, vol = df["close"], df["high"], df["low"], df["open"], df["volume"]
    e50, e200, r, a, vavg = (
        ema(close, 50),
        ema(close, 200),
        rsi(close),
        atr(high, low, close),
        sma(vol, 20),
    )
    c, o = float(close.iloc[-1]), float(opn.iloc[-1])
    e50_v, e200_v, a_v = float(e50.iloc[-1]), float(e200.iloc[-1]), float(a.iloc[-1])
    r_now, r_prev = float(r.iloc[-1]), float(r.iloc[-2])
    r_min = float(r.iloc[-DIP_LOOKBACK:].min())
    vol_ratio = float(vol.iloc[-1] / vavg.iloc[-1]) if vavg.iloc[-1] else 0.0
    qv24 = quote_volume_24h(df)

    facts = [
        Fact(name="Slotkoers", value=c),
        Fact(name="EMA 50", value=e50_v),
        Fact(name="EMA 200", value=e200_v),
        Fact(name="RSI 14", value=r_now, note=f"vorige candle {r_prev:.1f}"),
        Fact(name=f"Laagste RSI laatste {DIP_LOOKBACK} candles", value=r_min),
        Fact(name="ATR 14", value=a_v),
        Fact(name="Volume t.o.v. 20-gem.", value=vol_ratio),
        Fact(name="Omzet 24u (quote)", value=qv24),
    ]

    liquidity_ok = qv24 >= ctx.costs.min_quote_volume_24h
    if not liquidity_ok:
        return no_trade(ctx, df, "te weinig liquiditeit (24u-omzet onder minimum)", facts, False)
    if not (e50_v > e200_v and c > e200_v):
        return no_trade(ctx, df, "geen opwaartse trend (EMA 50 niet boven EMA 200)", facts)
    if r_min >= RSI_DIP:
        return no_trade(ctx, df, f"geen pullback (RSI kwam niet onder {RSI_DIP:.0f})", facts)
    if not (r_now > r_prev and c > o):
        return no_trade(ctx, df, "pullback nog niet gekeerd (RSI of candle niet omhoog)", facts)
    if r_now > RSI_MAX_ENTRY:
        return no_trade(ctx, df, "instap te laat (RSI al boven 60)", facts)

    stop = c - STOP_ATR * a_v
    target = c + TARGET_R * (c - stop)
    costs = _costs(ctx.costs)
    rr = rr_after_costs(c, stop, target, costs)
    if rr < MIN_RR:
        return no_trade(ctx, df, f"risico/rendement na kosten te laag ({rr:.2f} < {MIN_RR})", facts)

    points = sum(
        [
            vol_ratio >= 1.2,
            (e50_v - e200_v) / e200_v > 0.01,
            r_min < 35,
        ]
    )
    strength: Strength = "sterk" if points == 3 else "matig" if points == 2 else "zwak"

    assumptions = [
        "De opwaartse trend zet door na de pullback.",
        "Instap gebeurt rond de open van de volgende candle (dicht bij de slotkoers).",
        "Kosten volgens config/costs.yaml"
        + (" (tarieven nog niet gecontroleerd)." if not ctx.costs.checked_on else "."),
        "Strategie is nog niet gebacktest: geen bewezen voorsprong.",
    ]
    return Signal(
        instrument=ctx.instrument,
        interval=ctx.interval,
        decision="TRADE",
        direction="long",
        entry=c,
        stop_loss=stop,
        target=target,
        rr_ratio=rr,
        strength=strength,
        invalidation="Candle sluit onder de stop of EMA 50 zakt onder EMA 200",
        facts=facts,
        assumptions=assumptions,
        data_source=ctx.data_source,
        last_candle_at=df["open_time"].iloc[-1].to_pydatetime(),
        data_delay_s=ctx.data_delay_s,
        cost_assumptions=costs,
        liquidity_ok=True,
        strategy_version=VERSION,
    )


@dataclass(frozen=True)
class Variant:
    """Afwijkingen van de basisregels, alleen voor onderzoek in backtests.

    De standaardwaarden zijn precies de live strategie; `evaluate` kent deze opties niet.
    """

    stop_atr: float = STOP_ATR
    target_r: float = TARGET_R
    max_cost_share: float | None = None  # kosten (heen en terug) als deel van de stopafstand
    htf: str | None = None  # bv. "1D": alleen als EMA 50 > EMA 200 op die tijdschaal


BASE = Variant()


def htf_trend(df: pd.DataFrame, htf: str) -> pd.Series:
    """EMA 50 > EMA 200 op een hogere tijdschaal, per candle van df, zonder vooruit te kijken.

    Een candle van de hogere tijdschaal telt pas mee als die gesloten is op het moment dat de
    candle van df sluit.
    """
    times = pd.DatetimeIndex(df["open_time"])
    step = times.to_series().diff().median()
    big = df.set_axis(times)["close"].resample(htf, label="left", closed="left").last().dropna()
    trend = (ema(big, 50) > ema(big, 200)).rename("up")
    closes_at = pd.DatetimeIndex(big.index) + pd.Timedelta(htf)  # vaste duur, bv. "1D" of "4h"
    # Zelfde tijdseenheid aan beide kanten (Parquet levert ms, berekeningen soms us).
    available = pd.DataFrame({"at": closes_at.as_unit("ns"), "up": trend.to_numpy()})
    bars = pd.DataFrame({"at": (times + step).as_unit("ns")})
    merged = pd.merge_asof(bars, available.sort_values("at"), on="at", direction="backward")
    return pd.Series(merged["up"].eq(True).to_numpy(), index=df.index)


def evaluate_all(
    df: pd.DataFrame,
    costs: CostModel,
    variant: Variant = BASE,
    regime_ok: pd.Series | None = None,
) -> pd.DataFrame:
    """Dezelfde regels als `evaluate`, maar voor elke candle tegelijk (voor backtests).

    Rij t gebruikt alleen candles <= t. Kolommen: `trade` (bool), `stop`, `target`, `atr`,
    `trend_ok` (EMA 50 boven EMA 200, voor de ongeldigverklaring). Een test bewaakt dat
    `trade` met de standaard `variant` gelijk is aan `evaluate(df.iloc[: t + 1])`.
    `regime_ok` (bool per rij) is een extra marktfilter, bv. de dagtrend van BTC.
    """
    close, high, low, opn, vol = df["close"], df["high"], df["low"], df["open"], df["volume"]
    e50, e200, r, a = ema(close, 50), ema(close, 200), rsi(close), atr(high, low, close)
    r_prev = r.shift(1)
    r_min = r.rolling(DIP_LOOKBACK, min_periods=1).min()
    qv24 = (close * vol).set_axis(pd.DatetimeIndex(df["open_time"])).rolling("24h").sum().to_numpy()

    stop = close - variant.stop_atr * a
    target = close + variant.target_r * (close - stop)
    c = _costs(costs)
    round_trip = close * (2 * c.taker_fee + c.spread + 2 * c.slippage)
    risk = (close - stop).abs() + round_trip
    rr = ((target - close).abs() - round_trip) / risk.where(risk > 0)

    enough = pd.Series(range(len(df)), index=df.index) >= MIN_HISTORY - 1
    trade = (
        enough
        & (qv24 >= costs.min_quote_volume_24h)
        & (e50 > e200)
        & (close > e200)
        & (r_min < RSI_DIP)
        & (r > r_prev)
        & (close > opn)
        & (r <= RSI_MAX_ENTRY)
        & (rr >= MIN_RR)
    )
    if variant.max_cost_share is not None:
        trade &= round_trip <= variant.max_cost_share * (close - stop)
    if variant.htf is not None:
        trade &= htf_trend(df, variant.htf)
    if regime_ok is not None:
        trade &= regime_ok.reindex(df.index, fill_value=False).astype(bool)
    return pd.DataFrame(
        {
            "trade": trade.fillna(False),
            "stop": stop,
            "target": target,
            "atr": a,
            "trend_ok": e50 > e200,
        },
        index=df.index,
    )
