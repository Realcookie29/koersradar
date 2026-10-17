"""Ophalen met paginering, alleen gesloten candles, en fallback naar tweede bron."""

import logging
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from koersradar.sources.base import DataSource, closed_only, empty_frame, normalize
from koersradar.timeutils import interval_delta

log = logging.getLogger(__name__)


@dataclass
class FetchOutcome:
    candles: pd.DataFrame
    source: DataSource
    used_fallback: bool


def fetch_range(
    source: DataSource, symbol: str, interval: str, since: datetime, now: datetime
) -> pd.DataFrame:
    """Haal alle GESLOTEN candles op vanaf `since`, pagina voor pagina."""
    step = interval_delta(interval)
    limit = source.max_limit()
    frames: list[pd.DataFrame] = []
    cursor = since
    while cursor < now - step:
        page = source.fetch_ohlcv(symbol, interval, cursor, limit)
        if page.empty:
            break
        frames.append(page)
        last = page["open_time"].iloc[-1].to_pydatetime()
        # Niet stoppen op een korte pagina: sommige bronnen (Coinbase) geven limit-1 terug.
        # Stop alleen bij een lege pagina (loop-conditie) of als er geen voortgang is.
        if last < cursor:
            break
        cursor = last + step
    if not frames:
        return empty_frame()
    return closed_only(normalize(pd.concat(frames)), interval, now)


def fetch_with_fallback(
    primary: DataSource,
    fallback: DataSource | None,
    symbol: str,
    interval: str,
    since: datetime,
    now: datetime,
) -> FetchOutcome:
    # Alleen bij een FOUT naar de fallback. Een lege uitkomst is normaal als er sinds
    # de vorige ronde nog geen nieuwe candle gesloten is; aanhoudend uitblijven van
    # data wordt door de kwaliteitscheck als 'delayed'/'stale' gemeld.
    try:
        df = fetch_range(primary, symbol, interval, since, now)
        return FetchOutcome(df, primary, used_fallback=False)
    except Exception as exc:  # netwerk, rate limit, geo-blokkade, ...
        log.warning("%s faalde voor %s %s: %s", primary.name, symbol, interval, exc)
        if fallback is None:
            raise
    df = fetch_range(fallback, symbol, interval, since, now)
    return FetchOutcome(df, fallback, used_fallback=True)
