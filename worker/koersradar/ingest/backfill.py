"""Historie ophalen naar Parquet (voor backtests) zonder database.

Voorbeeld:  python -m koersradar.ingest.backfill --days 30 --symbols BTC/USDT ETH/USDT
"""

import argparse
import logging
from datetime import timedelta

from koersradar.config import load_instruments
from koersradar.ingest.fetch import fetch_with_fallback
from koersradar.ingest.quality import assess
from koersradar.ingest.store import append_history
from koersradar.sources.registry import get_source
from koersradar.timeutils import utcnow


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--symbols", nargs="*", help="standaard: alles uit instruments.yaml")
    ap.add_argument("--market", choices=["crypto", "aex"])
    args = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    now = utcnow()
    for ins in load_instruments():
        if args.symbols and ins.symbol not in args.symbols:
            continue
        if args.market and ins.market != args.market:
            continue
        primary = get_source(ins.source)
        fallback = get_source(ins.fallback) if ins.fallback else None
        for interval in ins.intervals:
            out = fetch_with_fallback(
                primary, fallback, ins.symbol, interval, now - timedelta(days=args.days), now
            )
            total = append_history(out.source.name, ins.symbol, interval, out.candles)
            rep = assess(
                out.candles,
                interval,
                now,
                continuous=out.source.continuous,
                nominal_delay=out.source.nominal_delay,
            )
            print(
                f"{ins.symbol:10} {interval:4} via {out.source.name:9} "
                f"+{len(out.candles):5} (totaal {total:6})  {rep.status} {rep.detail or ''}"
            )


if __name__ == "__main__":
    main()
