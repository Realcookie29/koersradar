from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from koersradar.signals.model import CostAssumptions, Signal, rr_after_costs

COSTS = CostAssumptions(taker_fee=0.001, spread=0.0002, slippage=0.0005)
BASE = dict(
    instrument="BTC/USDT",
    interval="1h",
    data_source="binance",
    last_candle_at=datetime(2026, 10, 17, 11, tzinfo=UTC),
    data_delay_s=60,
    cost_assumptions=COSTS,
    liquidity_ok=True,
    strategy_version="baseline-0.1",
)


def test_no_trade_requires_reason():
    with pytest.raises(ValidationError):
        Signal(decision="NO_TRADE", **BASE)
    assert Signal(decision="NO_TRADE", no_trade_reason="R/R te laag", **BASE)


def test_trade_requires_levels():
    with pytest.raises(ValidationError):
        Signal(decision="TRADE", direction="long", entry=100, **BASE)


def test_long_level_order_enforced():
    ok = dict(
        decision="TRADE",
        direction="long",
        entry=100,
        stop_loss=97,
        target=106,
        invalidation="sluiting onder 97",
    )
    assert Signal(**ok, **BASE)
    with pytest.raises(ValidationError):
        Signal(**{**ok, "target": 99}, **BASE)


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        Signal(
            decision="TRADE",
            direction="long",
            entry=100,
            stop_loss=97,
            target=106,
            invalidation="x",
            **{**BASE, "last_candle_at": datetime(2026, 10, 17)},  # noqa: DTZ001
        )


def test_costs_lower_rr():
    raw = (106 - 100) / (100 - 97)
    after = rr_after_costs(100, 97, 106, COSTS)
    assert after < raw
    assert rr_after_costs(100, 97, 106, CostAssumptions(taker_fee=0, spread=0, slippage=0)) == raw
