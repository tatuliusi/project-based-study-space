from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..services.postgres_service import close_pool, ensure_schema
from .routes.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_schema()
    yield
    await close_pool()


app = FastAPI(
    title="Autonomous SWE Agent",
    description="Submit GitHub issues and let the agent implement fixes.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tasks_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
