import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

_CREATE_USER_CONTEXT = """
CREATE TABLE IF NOT EXISTS user_context (
    user_id     TEXT PRIMARY KEY,
    tier        TEXT NOT NULL DEFAULT 'free',
    issue_history JSONB NOT NULL DEFAULT '[]',
    tone_notes  TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def migrate() -> None:
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(_CREATE_USER_CONTEXT)
        print("Migration complete.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
