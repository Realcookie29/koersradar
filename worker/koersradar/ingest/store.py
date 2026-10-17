"""Lange historie als Parquet (voor backtests), los van de Postgres-vensters."""

import os
from pathlib import Path

import pandas as pd

from koersradar.sources.base import normalize


def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "./data"))


def parquet_path(source: str, symbol: str, interval: str) -> Path:
    safe = symbol.replace("/", "-")
    return data_dir() / "candles" / source / safe / f"{interval}.parquet"


def read_history(source: str, symbol: str, interval: str) -> pd.DataFrame:
    path = parquet_path(source, symbol, interval)
    return pd.read_parquet(path) if path.exists() else normalize(pd.DataFrame())


def append_history(source: str, symbol: str, interval: str, new: pd.DataFrame) -> int:
    """Voeg toe en ontdubbel; geeft totaal aantal rijen terug."""
    path = parquet_path(source, symbol, interval)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = normalize(pd.concat([read_history(source, symbol, interval), new]))
    merged.to_parquet(path, index=False)
    return len(merged)
