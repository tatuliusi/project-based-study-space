import asyncpg

db_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str) -> None:
    global db_pool
    db_pool = await asyncpg.create_pool(dsn)


async def close_pool() -> None:
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
