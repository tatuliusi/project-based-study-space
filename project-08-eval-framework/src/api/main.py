from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import datasets, runs, webhook
from src.config import settings
from src.services.postgres_service import PostgresService


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = PostgresService(dsn=settings.postgres_dsn)
    await db.init_schema()
    app.state.db = db
    yield


app = FastAPI(
    title="LLM Eval & Quality Gate",
    version="0.1.0",
    description="Evaluation framework with LLM-as-judge and CI regression gating.",
    lifespan=lifespan,
)

app.include_router(datasets.router)
app.include_router(runs.router)
app.include_router(webhook.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
