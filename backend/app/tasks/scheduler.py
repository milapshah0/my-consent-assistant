import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.tasks.extract_keywords import extract_keywords
from app.tasks.generate_embeddings import generate_embeddings
from app.tasks.generate_summaries import generate_summaries
from app.tasks.relationships import analyze_relationships
from app.tasks.sync_aha import sync_aha_features
from app.tasks.sync_confluence import sync_confluence_pages

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.settings = get_settings()
        self._configured = False

    def configure(self) -> None:
        if self._configured:
            return

        interval = max(self.settings.sync_interval_minutes, 5)

        self.scheduler.add_job(
            sync_confluence_pages,
            trigger=IntervalTrigger(minutes=interval),
            id="sync_confluence",
            replace_existing=True,
            max_instances=1,
            kwargs={"force": False},
        )

        self.scheduler.add_job(
            generate_embeddings,
            trigger=IntervalTrigger(minutes=30),
            id="generate_embeddings",
            replace_existing=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            extract_keywords,
            trigger=IntervalTrigger(minutes=30),
            id="extract_keywords",
            replace_existing=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            analyze_relationships,
            trigger=IntervalTrigger(hours=1),
            id="analyze_relationships",
            replace_existing=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            generate_summaries,
            trigger=CronTrigger(hour=23, minute=0),
            id="daily_summary_placeholder",
            replace_existing=True,
            max_instances=1,
        )

        self._configured = True

    def start(self) -> None:
        self.configure()
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped")


scheduler_service = SchedulerService()
