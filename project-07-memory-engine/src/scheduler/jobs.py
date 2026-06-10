from __future__ import annotations

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.consolidation.graph import consolidation_graph
from src.services.postgres_service import PostgresService

logger = logging.getLogger(__name__)

_CRON = os.getenv("CONSOLIDATION_CRON", "0 2 * * *")

_postgres = PostgresService(
    dsn=os.getenv(
        "POSTGRES_DSN",
        "postgresql+asyncpg://memory:memory@localhost:5432/memoryengine",
    )
)


async def _run_consolidation_for_all_users() -> None:
    """Fetch all distinct user_ids from episodes and run consolidation for each."""
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.services.postgres_service import EpisodeRow

    engine = create_async_engine(
        os.getenv(
            "POSTGRES_DSN",
            "postgresql+asyncpg://memory:memory@localhost:5432/memoryengine",
        )
    )
    async with engine.connect() as conn:
        result = await conn.execute(sa.select(EpisodeRow.user_id).distinct())
        user_ids = [row[0] for row in result.fetchall()]
    await engine.dispose()

    for user_id in user_ids:
        logger.info("Running consolidation for user %s", user_id)
        try:
            await consolidation_graph.ainvoke({"user_id": user_id})
        except Exception:
            logger.exception("Consolidation failed for user %s", user_id)


def _consolidation_job() -> None:
    asyncio.get_event_loop().run_until_complete(_run_consolidation_for_all_users())


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    cron_parts = _CRON.split()
    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
        timezone="UTC",
    )
    scheduler.add_job(
        _run_consolidation_for_all_users,
        trigger=trigger,
        id="nightly_consolidation",
        replace_existing=True,
    )
    return scheduler
