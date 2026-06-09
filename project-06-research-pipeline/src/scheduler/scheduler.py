import asyncio
import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.services.redis_service import (
    acquire_schedule_lock,
    create_job,
    release_schedule_lock,
    set_job_status,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_scheduled_pipeline(schedule_id: str, topic: str) -> None:
    from src.graph.pipeline import pipeline

    if not await acquire_schedule_lock(schedule_id):
        logger.info("Schedule %s already running; skipping.", schedule_id)
        return

    job_id = str(uuid.uuid4())
    await create_job(job_id, topic)
    await set_job_status(job_id, "running")

    try:
        initial_state = {
            "job_id": job_id,
            "topic": topic,
            "sub_topics": [],
            "findings": [],
            "fact_check_results": [],
            "report": None,
            "artifact_url": None,
            "status": "running",
            "error": None,
        }
        await pipeline.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("Scheduled pipeline failed for job %s: %s", job_id, exc)
        await set_job_status(job_id, "failed", error=str(exc))
    finally:
        await release_schedule_lock(schedule_id)


def add_schedule(schedule_id: str, topic: str, cron_expression: str) -> None:
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("cron_expression must have exactly 5 fields (min hour dom mon dow)")

    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
    )

    scheduler.add_job(
        _run_scheduled_pipeline,
        trigger=trigger,
        id=schedule_id,
        args=[schedule_id, topic],
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Added schedule %s for topic '%s' with cron '%s'", schedule_id, topic, cron_expression)


def remove_schedule(schedule_id: str) -> bool:
    job = scheduler.get_job(schedule_id)
    if job is None:
        return False
    scheduler.remove_job(schedule_id)
    return True


def list_schedules() -> list[dict]:
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
