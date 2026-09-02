from __future__ import annotations

import json
from typing import Any

import asyncpg

from ..config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def ensure_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                issue_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                current_step TEXT NOT NULL DEFAULT '',
                state_json JSONB,
                pr_url TEXT,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )


async def insert_task(task_id: str, issue_url: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tasks (id, issue_url, status) VALUES ($1, $2, 'queued')",
            task_id,
            issue_url,
        )


async def update_task(task_id: str, **fields: Any) -> None:
    pool = await get_pool()
    set_clauses = []
    values: list[Any] = []
    for i, (key, value) in enumerate(fields.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value if not isinstance(value, dict) else json.dumps(value))
    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = ${len(values)}"
    async with pool.acquire() as conn:
        await conn.execute(query, *values)


async def get_task(task_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        return dict(row) if row else None


async def get_task_state(task_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT state_json FROM tasks WHERE id = $1", task_id)
        if row and row["state_json"]:
            return json.loads(row["state_json"])
        return None
