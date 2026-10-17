from datetime import UTC, datetime
from types import SimpleNamespace

from koersradar.explain.llm import explain
from koersradar.explain.number_check import extract_numbers, unsupported_numbers
from koersradar.signals.model import CostAssumptions, Fact, Signal

SIG = Signal(
    instrument="BTC/USDT",
    interval="1h",
    decision="TRADE",
    direction="long",
    entry=64123.45,
    stop_loss=63000.0,
    target=66370.35,
    rr_ratio=1.83,
    strength="matig",
    invalidation="Candle sluit onder de stop",
    facts=[Fact(name="RSI 14", value=38.27)],
    assumptions=["Trend zet door."],
    data_source="binance",
    last_candle_at=datetime(2026, 10, 17, 12, tzinfo=UTC),
    data_delay_s=60,
    cost_assumptions=CostAssumptions(taker_fee=0.001, spread=0.0002, slippage=0.0005),
    liquidity_ok=True,
    strategy_version="trend-pullback-0.1",
)


class FakeClient:
    def __init__(self, text: str, stop: str = "end_turn"):
        self.messages = SimpleNamespace(
            create=lambda **kw: SimpleNamespace(
                stop_reason=stop, content=[SimpleNamespace(type="text", text=text)]
            )
        )


def test_parses_dutch_numbers():
    assert extract_numbers("instap 64.123,45 en RSI 38,3") == [(64123.45, 2), (38.3, 1)]


def test_rounded_numbers_accepted_invented_rejected():
    allowed = [64123.45, 38.27]
    assert unsupported_numbers("Instap rond 64.123 bij RSI 38,3.", allowed, set()) == []
    assert unsupported_numbers("Kans op winst 85%.", allowed, set()) == [85.0]


def test_explain_ok():
    text = "Feiten: RSI 14 staat op 38,3; instap 64.123,45.\nAannames: trend zet door."
    exp = explain(SIG, client=FakeClient(text))
    assert exp.status == "ok" and exp.text == text


def test_explain_rejects_invented_number():
    exp = explain(SIG, client=FakeClient("Feiten: 73% kans op het koersdoel."))
    assert exp.status == "rejected" and exp.text is None


def test_explain_rejects_truncated():
    assert explain(SIG, client=FakeClient("Feiten:", stop="max_tokens")).status == "rejected"


def test_no_trade_is_not_explained():
    no = SIG.model_copy(update={"decision": "NO_TRADE", "no_trade_reason": "x"})
    assert explain(no, client=FakeClient("x")).status == "skipped"
