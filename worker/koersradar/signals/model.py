"""Signaalrecord — spiegelt public.signals in de database.

Onderscheid: facts = gemeten (controleerbaar), assumptions = aannames.
Kanspercentages horen hier bewust NIET in tot er kalibratie op testdata is.
"""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class Fact(BaseModel):
    name: str  # bv. "RSI(14)"
    value: float
    note: str | None = None  # bv. "onder 35 = pullback"


class CostAssumptions(BaseModel):
    taker_fee: float
    spread: float
    slippage: float


class Signal(BaseModel):
    instrument: str
    interval: str
    decision: Literal["TRADE", "NO_TRADE"]
    direction: Literal["long", "short"] | None = None
    entry: float | None = None
    invalidation: str | None = None
    stop_loss: float | None = None
    target: float | None = None
    rr_ratio: float | None = None
    strength: Literal["zwak", "matig", "sterk"] | None = None
    facts: list[Fact] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    no_trade_reason: str | None = None
    data_source: str
    last_candle_at: datetime
    data_delay_s: int
    cost_assumptions: CostAssumptions
    liquidity_ok: bool
    strategy_version: str

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.decision == "NO_TRADE":
            if not self.no_trade_reason:
                raise ValueError("NO_TRADE vereist een no_trade_reason")
            return self
        missing = [
            f
            for f in ("direction", "entry", "stop_loss", "target", "invalidation")
            if getattr(self, f) is None
        ]
        if missing:
            raise ValueError(f"TRADE mist velden: {missing}")
        assert self.entry is not None and self.stop_loss is not None and self.target is not None
        if self.direction == "long" and not (self.stop_loss < self.entry < self.target):
            raise ValueError("long: verwacht stop < entry < target")
        if self.direction == "short" and not (self.target < self.entry < self.stop_loss):
            raise ValueError("short: verwacht target < entry < stop")
        if self.last_candle_at.tzinfo is None:
            raise ValueError("last_candle_at moet timezone-aware (UTC) zijn")
        return self


def rr_after_costs(entry: float, stop: float, target: float, costs: CostAssumptions) -> float:
    """Risico-rendement na kosten: round-trip fee + spread + slippage gaan van de winst af
    en komen bij het risico."""
    round_trip = entry * (2 * costs.taker_fee + costs.spread + 2 * costs.slippage)
    reward = abs(target - entry) - round_trip
    risk = abs(entry - stop) + round_trip
    return reward / risk if risk > 0 else 0.0
