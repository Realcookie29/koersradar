from collections.abc import Callable

from koersradar.sources.base import DataSource


def _yfinance() -> DataSource:
    from koersradar.sources.yfinance_source import YFinanceSource

    return YFinanceSource()


def _binance() -> DataSource:
    from koersradar.sources.ccxt_source import binance

    return binance()


def _coinbase() -> DataSource:
    from koersradar.sources.ccxt_source import coinbase

    return coinbase()


_FACTORIES: dict[str, Callable[[], DataSource]] = {
    "binance": _binance,
    "coinbase": _coinbase,
    "yfinance": _yfinance,
}


def get_source(name: str) -> DataSource:
    try:
        return _FACTORIES[name]()
    except KeyError:
        raise ValueError(f"Onbekende bron: {name!r}. Beschikbaar: {sorted(_FACTORIES)}") from None
