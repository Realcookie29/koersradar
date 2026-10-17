"""AEX via yfinance — EXPERIMENTEEL.

Onofficieel (niet gelieerd aan Yahoo), Yahoo-data is 'personal use only', kan zonder
aankondiging breken. 15m-historie max 60 dagen, 1h max 730 dagen. Zie docs/data-voorwaarden.md.
"""

from datetime import datetime, timedelta

import pandas as pd

from koersradar.sources.base import empty_frame, normalize

_YF_INTERVAL = {"15m": "15m", "1h": "60m"}
_MAX_DAYS = {"15m": 59, "1h": 729}


class YFinanceSource:
    name = "yfinance"
    continuous = False  # beurs heeft openingstijden
    nominal_delay = timedelta(minutes=15)  # Euronext via Yahoo is doorgaans vertraagd

    def fetch_ohlcv(
        self, symbol: str, interval: str, since: datetime | None, limit: int
    ) -> pd.DataFrame:
        import yfinance as yf  # optionele dependency: pip install ".[aex]"

        period_days = _MAX_DAYS[interval]
        raw = yf.Ticker(symbol).history(
            period=f"{period_days}d", interval=_YF_INTERVAL[interval], auto_adjust=False
        )
        if raw.empty:
            return empty_frame()
        df = raw.reset_index().rename(
            columns={
                raw.index.name or "Datetime": "open_time",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        df = normalize(df)
        if since is not None:
            df = df[df["open_time"] >= pd.Timestamp(since)]
        return df.tail(limit).reset_index(drop=True)

    def max_limit(self) -> int:
        return 10_000
