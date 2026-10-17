"""Crypto-koersen via CCXT (MIT). Alleen publieke marktdata: geen API-keys, geen orders."""

from datetime import datetime, timedelta
from typing import Any

import ccxt
import pandas as pd

from koersradar.sources.base import OHLCV_COLUMNS, empty_frame, normalize

# Binance heeft een aparte host zonder keys voor alleen marktdata.
BINANCE_MARKET_DATA_URL = "https://data-api.binance.vision/api/v3"


class CcxtSource:
    continuous = True
    nominal_delay = timedelta(0)

    def __init__(self, name: str, exchange: Any, quote_map: dict[str, str] | None = None):
        self.name = name
        self._ex = exchange
        # Sommige exchanges noteren tegen USD i.p.v. USDT (bv. Coinbase).
        self._quote_map = quote_map or {}

    def _map_symbol(self, symbol: str) -> str:
        base, quote = symbol.split("/")
        return f"{base}/{self._quote_map.get(quote, quote)}"

    def fetch_ohlcv(
        self, symbol: str, interval: str, since: datetime | None, limit: int
    ) -> pd.DataFrame:
        since_ms = int(since.timestamp() * 1000) if since else None
        rows = self._ex.fetch_ohlcv(self._map_symbol(symbol), interval, since_ms, limit)
        if not rows:
            return empty_frame()
        df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        return normalize(df)

    def max_limit(self) -> int:
        return 300 if self.name == "coinbase" else 1000


def binance() -> CcxtSource:
    ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    ex.urls["api"]["public"] = BINANCE_MARKET_DATA_URL
    # Alleen spot-markten laden (anders probeert CCXT ook futures-endpoints).
    ex.options["fetchMarkets"] = {"types": ["spot"]}
    return CcxtSource("binance", ex)


def coinbase() -> CcxtSource:
    ex = ccxt.coinbaseexchange({"enableRateLimit": True})
    return CcxtSource("coinbase", ex, quote_map={"USDT": "USD"})
