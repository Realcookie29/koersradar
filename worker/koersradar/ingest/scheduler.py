"""Draait de ingest elke 15 minuten, 1 minuut na het sluiten van een candle."""

import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

from koersradar.ingest.run import ingest_once

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    sched = BlockingScheduler(timezone="UTC")
    # :01, :16, :31, :46 — exchanges hebben de candle dan afgerond.
    sched.add_job(ingest_once, "cron", minute="1,16,31,46", max_instances=1, coalesce=True)
    log.info("Scheduler gestart; eerste run direct.")
    ingest_once()
    sched.start()


if __name__ == "__main__":
    main()
