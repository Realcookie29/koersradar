"""Speelt signalen candle voor candle na, met kosten, zonder in de toekomst te kijken.

Regels (zie docs/plan.md, "Veilig testen"):
- Een signaal op de slotkoers van candle t wordt uitgevoerd op de open van candle t+1.
- Opent t+1 al onder de stop of boven het doel, dan wordt de trade overgeslagen.
- Daarna per candle: raakt de low de stop, dan uit op de stop (of op de open bij een gat);
  raakt de high het doel, dan uit op het doel. Raakt één candle beide, dan telt de stop
  (voorzichtigste aanname, want de volgorde binnen de candle is onbekend).
- Sluit een candle met EMA 50 onder EMA 200, dan uit op de open van de volgende candle
  ("ongeldig", zoals de ongeldigverklaring in het signaal).
- Eén positie tegelijk per instrument. Open aan het eind van de periode: uit op de laatste slot.

Kosten per kant: taker-fee + halve spread + slippage (percentage + fractie van de ATR).
R-multiple = resultaat na kosten gedeeld door het geplande verlies bij een stop na kosten.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from koersradar.config import CostModel

ExitReason = Literal["stop", "doel", "ongeldig", "einde"]


@dataclass(frozen=True)
class Trade:
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry_price: float  # betaalde prijs per eenheid, incl. spread, slippage en fee
    stop: float
    target: float
    exit_time: pd.Timestamp
    exit_price: float  # ontvangen prijs per eenheid, na spread, slippage en fee
    exit_reason: ExitReason
    r_multiple: float
    return_pct: float
    bars_held: int
    entry_raw: float = float("nan")  # koers zonder kosten: de open van de instapcandle
    exit_raw: float = float("nan")  # koers zonder kosten: stop, doel, open of slot


@dataclass(frozen=True)
class SimResult:
    trades: list[Trade]
    bars: int  # aantal candles in de periode
    bars_in_trade: int
    skipped_gaps: int  # signalen overgeslagen omdat de open al voorbij stop of doel lag


def _side_cost(price: float, atr: float, costs: CostModel) -> float:
    """Slippage + halve spread als fractie van de prijs, voor één kant."""
    slip = costs.slippage_pct + (costs.slippage_atr_frac * atr / price if price > 0 else 0.0)
    return costs.spread / 2 + slip


def buy_cost(price: float, atr: float, costs: CostModel) -> float:
    return price * (1 + _side_cost(price, atr, costs)) * (1 + costs.taker_fee)


def sell_proceeds(price: float, atr: float, costs: CostModel) -> float:
    return price * (1 - _side_cost(price, atr, costs)) * (1 - costs.taker_fee)


def simulate(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    costs: CostModel,
    start: int = 0,
    end: int | None = None,
) -> SimResult:
    """Simuleer op rijen [start, end). `signals` komt uit `trend_pullback.evaluate_all` (of
    een andere bron met dezelfde kolommen: trade, stop, target, atr, trend_ok)."""
    end = len(df) if end is None else end
    times = df["open_time"].to_numpy()
    opn, high, low, close = (df[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close"))
    trade = signals["trade"].to_numpy(dtype=bool)
    stop_s, target_s = (
        signals["stop"].to_numpy(dtype=float),
        signals["target"].to_numpy(dtype=float),
    )
    atr_s, trend_ok = signals["atr"].to_numpy(dtype=float), signals["trend_ok"].to_numpy(dtype=bool)

    trades: list[Trade] = []
    skipped = in_trade_bars = 0
    pending: int | None = None  # rij van het signaal dat op de volgende open instapt
    pos: dict | None = None
    exit_next_open = False

    def close_pos(b: int, raw_price: float, reason: ExitReason) -> None:
        nonlocal pos
        assert pos is not None
        proceeds = sell_proceeds(raw_price, pos["atr"], costs)
        trades.append(
            Trade(
                signal_time=pd.Timestamp(times[pos["signal"]]),
                entry_time=pd.Timestamp(times[pos["entry"]]),
                entry_price=pos["cost"],
                stop=pos["stop"],
                target=pos["target"],
                exit_time=pd.Timestamp(times[b]),
                exit_price=proceeds,
                exit_reason=reason,
                r_multiple=(proceeds - pos["cost"]) / pos["risk"],
                return_pct=proceeds / pos["cost"] - 1,
                bars_held=b - pos["entry"] + 1,
                entry_raw=pos["raw"],
                exit_raw=float(raw_price),
            )
        )
        pos = None

    for b in range(start, end):
        if pos is not None and exit_next_open:
            close_pos(b, opn[b], "ongeldig")
            exit_next_open = False

        if pos is None and pending is not None:
            s = pending
            pending = None
            stop, target, a = stop_s[s], target_s[s], atr_s[s]
            if opn[b] <= stop or opn[b] >= target:
                skipped += 1
            else:
                cost = buy_cost(opn[b], a, costs)
                risk = cost - sell_proceeds(stop, a, costs)
                pos = {
                    "signal": s,
                    "entry": b,
                    "stop": stop,
                    "target": target,
                    "atr": a,
                    "cost": cost,
                    "risk": risk,
                    "raw": float(opn[b]),
                }

        if pos is not None:
            in_trade_bars += 1
            if low[b] <= pos["stop"]:
                close_pos(b, min(opn[b], pos["stop"]), "stop")
            elif high[b] >= pos["target"]:
                close_pos(b, max(opn[b], pos["target"]), "doel")
            elif not trend_ok[b]:
                exit_next_open = True

        if pos is None and trade[b] and b + 1 < end:
            pending = b

    if pos is not None:
        close_pos(end - 1, close[end - 1], "einde")

    return SimResult(
        trades=trades, bars=end - start, bars_in_trade=in_trade_bars, skipped_gaps=skipped
    )


def trades_frame(trades: list[Trade]) -> pd.DataFrame:
    return pd.DataFrame([t.__dict__ for t in trades])


def random_signals(
    signals: pd.DataFrame, prob: float, rng: np.random.Generator, eligible: np.ndarray
) -> pd.DataFrame:
    """Willekeurige instappen met dezelfde stop/doel-regels (benchmark 'random entry')."""
    pick = (rng.random(len(signals)) < prob) & eligible
    return signals.assign(trade=pick)
