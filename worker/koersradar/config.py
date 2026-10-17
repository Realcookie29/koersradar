"""Laadt config/instruments.yaml en config/costs.yaml."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "config"


def config_dir() -> Path:
    return Path(os.environ.get("KOERSRADAR_CONFIG_DIR", _DEFAULT_DIR))


@dataclass(frozen=True)
class Instrument:
    symbol: str  # canoniek, bv. BTC/USDT of ASML.AS
    market: str  # crypto | aex
    source: str
    fallback: str | None
    intervals: tuple[str, ...]
    experimental: bool


@dataclass(frozen=True)
class CostModel:
    taker_fee: float
    spread: float
    slippage_pct: float
    slippage_atr_frac: float
    min_quote_volume_24h: float
    checked_on: str | None


def load_instruments(path: Path | None = None) -> list[Instrument]:
    raw = yaml.safe_load((path or config_dir() / "instruments.yaml").read_text())
    out: list[Instrument] = []
    for market, cfg in raw.items():
        quote = cfg.get("quote")
        for sym in cfg["symbols"]:
            out.append(
                Instrument(
                    symbol=f"{sym}/{quote}" if quote else sym,
                    market=market,
                    source=cfg["source"],
                    fallback=cfg.get("fallback"),
                    intervals=tuple(cfg["intervals"]),
                    experimental=bool(cfg.get("experimental", False)),
                )
            )
    return out


def load_costs(path: Path | None = None) -> dict[str, CostModel]:
    raw = yaml.safe_load((path or config_dir() / "costs.yaml").read_text())
    return {name: CostModel(**vals) for name, vals in raw.items()}
