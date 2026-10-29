"""Langere 1h-historie in de database zetten, voor 4-uurs- en daggrafieken in het portaal.

De gewone ingest bewaart 45 dagen bij de eerste start. Een daggrafiek met EMA 200 heeft meer
nodig; de bewaartermijn voor 1h in de database is 730 dagen (db.RETENTION).

Voorbeeld:  python -m koersradar.ingest.history_db --days 400
"""

import argparse
import logging
from datetime import timedelta

from koersradar import db
from koersradar.config import load_instruments
from koersradar.ingest.fetch import fetch_with_fallback
from koersradar.sources.registry import get_source
from koersradar.timeutils import utcnow

INTERVAL = "1h"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument("--market", choices=["crypto", "aex"], default="crypto")
    args = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    now = utcnow()
    instruments = [
        i for i in load_instruments() if i.market == args.market and INTERVAL in i.intervals
    ]
    with db.connect() as conn:
        ids = db.ensure_instruments(conn, load_instruments())
        for ins in instruments:
            primary = get_source(ins.source)
            fallback = get_source(ins.fallback) if ins.fallback else None
            out = fetch_with_fallback(
                primary, fallback, ins.symbol, INTERVAL, now - timedelta(days=args.days), now
            )
            db.upsert_candles(conn, ids[ins.symbol], INTERVAL, out.source.name, out.candles)
            conn.commit()
            print(f"{ins.symbol:10} {len(out.candles):6} candles ({out.source.name})")


if __name__ == "__main__":
    main()
