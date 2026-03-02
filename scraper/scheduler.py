import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def job() -> None:
    from scraper.runner import run_queries

    logger.info("Daily scrape started.")
    try:
        total = run_queries(delay=5.0)
        logger.info("Daily scrape complete. %d records written.", total)
    except Exception as e:
        logger.error("Daily scrape failed: %s", e, exc_info=True)


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(
        job,
        CronTrigger(hour=10, minute=0, timezone="America/Chicago"),
    )
    logger.info("Scheduler started. Runs daily at 10:00 AM America/Chicago.")
    scheduler.start()
