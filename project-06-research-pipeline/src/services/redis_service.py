import json
import os
from typing import Literal

import redis.asyncio as aioredis

from src.graph.state import Report

JobStatus = Literal["queued", "running", "done", "failed"]

_DEFAULT_TTL = int(os.getenv("REPORT_TTL_SECONDS", "86400"))


def _client() -> aioredis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return aioredis.from_url(url, decode_responses=False)


async def create_job(job_id: str, topic: str) -> None:
    r = _client()
    meta = json.dumps({"job_id": job_id, "topic": topic, "status": "queued"})
    await r.setex(f"job:{job_id}:meta", _DEFAULT_TTL, meta)
    await r.aclose()


async def set_job_status(job_id: str, status: JobStatus, error: str | None = None) -> None:
    r = _client()
    raw = await r.get(f"job:{job_id}:meta")
    if raw:
        meta = json.loads(raw)
        meta["status"] = status
        if error:
            meta["error"] = error
        await r.setex(f"job:{job_id}:meta", _DEFAULT_TTL, json.dumps(meta))
    await r.aclose()


async def get_job_status(job_id: str) -> dict | None:
    r = _client()
    raw = await r.get(f"job:{job_id}:meta")
    await r.aclose()
    if raw is None:
        return None
    return json.loads(raw)


async def get_report_json(job_id: str) -> dict | None:
    r = _client()
    raw = await r.get(f"report:{job_id}:json")
    await r.aclose()
    if raw is None:
        return None
    return json.loads(raw)


async def get_report_pdf(job_id: str) -> bytes | None:
    r = _client()
    data = await r.get(f"report:{job_id}:pdf")
    await r.aclose()
    return data


async def acquire_schedule_lock(schedule_id: str) -> bool:
    r = _client()
    acquired = await r.set(f"schedule:{schedule_id}:running", "1", nx=True, ex=3600)
    await r.aclose()
    return bool(acquired)


async def release_schedule_lock(schedule_id: str) -> None:
    r = _client()
    await r.delete(f"schedule:{schedule_id}:running")
    await r.aclose()
