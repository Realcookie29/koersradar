"""Worker-loop: ingest + scan elke 15 minuten, en handmatige scans vanuit het portaal."""

import logging
import os
import threading

from apscheduler.schedulers.blocking import BlockingScheduler

from koersradar import db
from koersradar.ingest.run import ingest_once
from koersradar.scanner.run import run_scan

log = logging.getLogger(__name__)
_lock = threading.Lock()  # nooit twee ingest/scan-rondes tegelijk


def scheduled_round() -> None:
    with _lock:
        ingest_once()
        run_scan("schedule")


def poll_manual_requests() -> None:
    """Knop 'Scan nu' in het portaal maakt een pending scan_run aan; die pakken we hier op."""
    if _lock.locked():
        return  # er loopt al een ronde; de aanvraag wordt na afloop opgepakt
    with db.connect() as conn:
        run_id = db.claim_pending_manual_run(conn)
        conn.commit()
    if run_id is None:
        return
    with _lock:
        log.info("Handmatige scan %s: eerst verse data ophalen", run_id)
        ingest_once()
        run_scan("manual", run_id=run_id)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    sched = BlockingScheduler(timezone="UTC")
    # :01, :16, :31, :46 — exchanges hebben de candle dan afgerond.
    sched.add_job(scheduled_round, "cron", minute="1,16,31,46", max_instances=1, coalesce=True)
    sched.add_job(poll_manual_requests, "interval", seconds=20, max_instances=1, coalesce=True)
    log.info("Scheduler gestart; eerste ronde direct.")
    scheduled_round()
    sched.start()


if __name__ == "__main__":
    main()
