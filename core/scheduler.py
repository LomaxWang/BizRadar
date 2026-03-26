"""APScheduler-based background scheduler for periodic pipeline runs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)


def _scheduled_run(source: str, settings: "Settings") -> None:
    """Execute a single pipeline run for *source*. Called by APScheduler."""
    from core.orchestrator import run_pipeline

    logger.info("Scheduler: starting pipeline for source=%s", source)
    try:
        stats = run_pipeline(
            source=source,
            mode="daily_report",
            settings=settings,
        )
        logger.info(
            "Scheduler: source=%s finished — fetched=%d approved=%d errors=%d",
            source,
            stats.fetched,
            stats.approved,
            stats.errors,
        )
    except Exception:
        logger.exception("Scheduler: pipeline failed for source=%s", source)


def start_scheduler(settings: "Settings") -> BackgroundScheduler:
    """Create, configure and start a :class:`BackgroundScheduler`.

    A cron job is added for **each** source listed in
    ``settings.schedule_sources`` using the cron expression from
    ``settings.schedule_cron``.

    Returns the running scheduler instance so the caller can shut it down
    later via ``scheduler.shutdown()``.
    """
    scheduler = BackgroundScheduler()
    trigger = CronTrigger.from_crontab(settings.schedule_cron)

    for source in settings.schedule_sources:
        job_id = f"ideahunter_{source}"
        scheduler.add_job(
            _scheduled_run,
            trigger=trigger,
            args=[source, settings],
            id=job_id,
            name=f"IdeaHunter scan: {source}",
            replace_existing=True,
        )
        logger.info(
            "Scheduler: registered job %s (cron=%s)", job_id, settings.schedule_cron
        )

    scheduler.start()
    logger.info("Scheduler started with %d job(s)", len(settings.schedule_sources))
    return scheduler
