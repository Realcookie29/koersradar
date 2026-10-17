"""AI-uitleg bij een TRADE-signaal via Claude.

Het model krijgt ALLEEN het berekende signaal (JSON) en schrijft daar een korte
Nederlandse uitleg bij. Getallen in de uitleg worden gecontroleerd tegen de input.
"""

import json
import logging
import os
from dataclasses import dataclass

import anthropic

from koersradar.explain.number_check import extract_numbers, unsupported_numbers
from koersradar.signals.model import Signal

log = logging.getLogger(__name__)

# Haiku: goedkoop genoeg voor het budget (zie docs/plan.md). Overschrijfbaar via env.
DEFAULT_MODEL = "claude-haiku-5-5"
PROMPT_VERSION = "uitleg-v1"

SYSTEM = """Je bent de uitlegmodule van Koersradar, een beslisondersteunend dashboard voor \
een vriendengroep die leert daytraden. Je krijgt één signaal als JSON. Alle getallen \
daarin zijn berekend door gecontroleerde code.

Schrijf in het Nederlands, maximaal 120 woorden, met precies deze vier kopjes \
(elk op een eigen regel, gevolgd door 1-3 korte zinnen):
Feiten:
Aannames:
Risico's:
Wanneer ongeldig:

Regels:
- Gebruik uitsluitend getallen die letterlijk in de JSON staan (afronden mag). \
Reken niets uit en noem geen nieuwe getallen, percentages of kansen.
- Presenteer niets als zekerheid en beloof geen winst. Noem dat de strategie nog niet \
gebacktest is.
- Geen koop- of verkoopadvies in de gebiedende wijs; beschrijf wat het signaal inhoudt."""

# Getallen die zonder bron mogen voorkomen (periodes van indicatoren e.d.).
FREE_NUMBERS = {14.0, 20.0, 24.0, 50.0, 200.0, 1.0, 2.0, 15.0}


@dataclass
class Explanation:
    status: str  # ok | rejected | skipped | error
    text: str | None
    model: str | None


def _payload(sig: Signal) -> dict:
    data = sig.model_dump(mode="json", exclude={"cost_assumptions"})
    data["kosten_aannames"] = sig.cost_assumptions.model_dump()
    return data


def _allowed_numbers(sig: Signal) -> list[float]:
    nums: list[float] = []

    def walk(x: object) -> None:
        if isinstance(x, bool):
            return
        if isinstance(x, int | float):
            nums.append(float(x))
            nums.append(float(x) * 100)  # fracties mogen als percentage
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            nums.extend(v for v, _ in extract_numbers(x))

    walk(_payload(sig))
    return nums


def explain(sig: Signal, client: anthropic.Anthropic | None = None) -> Explanation:
    if sig.decision != "TRADE":
        return Explanation("skipped", None, None)
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        return Explanation("skipped", None, None)

    model = os.environ.get("KOERSRADAR_LLM_MODEL", DEFAULT_MODEL)
    client = client or anthropic.Anthropic(timeout=60.0)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=SYSTEM,
            output_config={"effort": "low"},
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(_payload(sig), ensure_ascii=False, indent=1),
                }
            ],
        )
    except anthropic.RateLimitError:
        log.warning("LLM rate limit; uitleg overgeslagen")
        return Explanation("error", None, model)
    except anthropic.APIStatusError as exc:
        log.warning("LLM fout %s: %s", exc.status_code, exc.message)
        return Explanation("error", None, model)
    except anthropic.APIConnectionError:
        log.warning("LLM niet bereikbaar")
        return Explanation("error", None, model)

    if response.stop_reason != "end_turn":
        log.warning("LLM stop_reason=%s; uitleg niet gebruikt", response.stop_reason)
        return Explanation("rejected", None, model)
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    bad = unsupported_numbers(text, _allowed_numbers(sig), FREE_NUMBERS)
    if bad:
        log.warning("Uitleg afgewezen, onbekende getallen: %s", bad)
        return Explanation("rejected", None, model)
    return Explanation("ok", text, model)
