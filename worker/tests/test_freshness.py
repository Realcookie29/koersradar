from datetime import UTC, datetime

from koersradar.ingest.quality import QualityReport
from koersradar.signals.freshness import freshness_gate

T = datetime(2026, 10, 17, tzinfo=UTC)


def test_ok_passes():
    assert freshness_gate(QualityReport("ok", T)).ok


def test_blocking_statuses():
    for status in ("stale", "gap", "error", "delayed"):
        res = freshness_gate(QualityReport(status, T, detail="x"))
        assert not res.ok and res.reason


def test_delayed_can_be_allowed():
    assert freshness_gate(QualityReport("delayed", T), allow_delayed=True).ok


def test_no_data_blocks():
    assert freshness_gate(QualityReport("ok", None)).reason == "geen data"
