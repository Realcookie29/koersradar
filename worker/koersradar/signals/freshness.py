"""Versheidspoort: zonder verse, volledige data geen signaal.

Wordt aangeroepen VOOR de strategie draait. Faalt de poort, dan wordt er een
NO_TRADE-record met reden opgeslagen in plaats van een signaal.
"""

from dataclasses import dataclass

from koersradar.ingest.quality import QualityReport


@dataclass(frozen=True)
class GateResult:
    ok: bool
    reason: str | None = None


_BLOCKING = {
    "stale": "data verouderd",
    "gap": "ontbrekende candles in het venster",
    "error": "data onvolledig of fout",
    "delayed": "data vertraagd",
}


def freshness_gate(report: QualityReport, *, allow_delayed: bool = False) -> GateResult:
    if report.last_candle_at is None:
        return GateResult(False, "geen data")
    if report.status == "ok" or (report.status == "delayed" and allow_delayed):
        return GateResult(True)
    reason = _BLOCKING.get(report.status, f"onbekende status {report.status}")
    if report.detail:
        reason = f"{reason} ({report.detail})"
    return GateResult(False, reason)
