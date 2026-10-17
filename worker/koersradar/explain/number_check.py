"""Controle: elk getal in de AI-uitleg moet terug te voeren zijn op de input.

Het taalmodel mag uitleggen, niet rekenen of verzinnen. Een uitleg met een getal
dat niet (afgerond) in het signaal voorkomt, wordt afgewezen.
"""

import re

# Getallen met optioneel duizendtal-punten en decimale komma (NL) of punt (EN).
_NUMBER = re.compile(r"(?<![\w.,])[-+]?\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|[-+]?\d+(?:[.,]\d+)?")


def _parse(token: str) -> tuple[float, int] | None:
    t = token.replace(" ", "")
    if re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+(?:,\d+)?", t):  # 64.123,45
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        value = float(t)
    except ValueError:
        return None
    decimals = len(t.split(".")[1]) if "." in t else 0
    return value, decimals


def extract_numbers(text: str) -> list[tuple[float, int]]:
    out = []
    for m in _NUMBER.finditer(text):
        parsed = _parse(m.group())
        if parsed is not None:
            out.append(parsed)
    return out


def unsupported_numbers(text: str, allowed: list[float], free: set[float]) -> list[float]:
    """Getallen uit `text` die niet passen bij `allowed` (afgerond) en niet in `free` staan."""
    bad = []
    for value, decimals in extract_numbers(text):
        if abs(value) in free:
            continue
        tol = 0.5 * 10 ** (-decimals) + 1e-9
        if not any(abs(abs(value) - abs(a)) <= max(tol, 0.005 * abs(a)) for a in allowed):
            bad.append(value)
    return bad
