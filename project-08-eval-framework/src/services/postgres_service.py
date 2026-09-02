from __future__ import annotations

import json
from typing import Any

import asyncpg

from src.models import Dataset, EvalReport, EvalRun


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    metric_set TEXT NOT NULL,
    version TEXT NOT NULL,
    samples TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id),
    app_config TEXT NOT NULL,
    baseline_run_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eval_reports (
    run_id TEXT PRIMARY KEY REFERENCES eval_runs(id),
    dataset_id TEXT NOT NULL,
    app_config TEXT NOT NULL,
    aggregated_scores TEXT NOT NULL,
    regression_report TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class PostgresService:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn)
        return self._pool

    async def init_schema(self) -> None:
        pool = await self._get_pool()
        await pool.execute(CREATE_TABLES)

    async def save_dataset(self, dataset: Dataset) -> None:
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO datasets (id, name, description, metric_set, version, samples)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE
              SET metric_set = EXCLUDED.metric_set,
                  version = EXCLUDED.version,
                  samples = EXCLUDED.samples
            """,
            dataset.id,
            dataset.name,
            dataset.description,
            json.dumps(dataset.metric_set),
            dataset.version,
            json.dumps([s.model_dump() for s in dataset.samples]),
        )

    async def get_dataset(self, dataset_id: str) -> Dataset | None:
        pool = await self._get_pool()
        row = await pool.fetchrow("SELECT * FROM datasets WHERE id = $1", dataset_id)
        if not row:
            return None
        data = dict(row)
        data["metric_set"] = json.loads(data["metric_set"])
        data["samples"] = json.loads(data["samples"])
        return Dataset(**data)

    async def list_datasets(self) -> list[Dataset]:
        pool = await self._get_pool()
        rows = await pool.fetch("SELECT * FROM datasets ORDER BY created_at DESC")
        result = []
        for row in rows:
            data = dict(row)
            data["metric_set"] = json.loads(data["metric_set"])
            data["samples"] = json.loads(data["samples"])
            result.append(Dataset(**data))
        return result

    async def save_run(self, run: EvalRun) -> None:
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO eval_runs (id, dataset_id, app_config, baseline_run_id, status)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
            """,
            run.id,
            run.dataset_id,
            json.dumps(run.app_config.model_dump()),
            run.baseline_run_id,
            run.status,
        )

    async def update_run_status(self, run_id: str, status: str) -> None:
        pool = await self._get_pool()
        await pool.execute(
            "UPDATE eval_runs SET status = $1 WHERE id = $2", status, run_id
        )

    async def save_report(self, report: EvalReport) -> None:
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO eval_reports (run_id, dataset_id, app_config, aggregated_scores, regression_report)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (run_id) DO NOTHING
            """,
            report.run_id,
            report.dataset_id,
            json.dumps(report.app_config.model_dump()),
            json.dumps({k: v.model_dump() for k, v in report.aggregated_scores.items()}),
            json.dumps(report.regression_report.model_dump()) if report.regression_report else None,
        )

    async def get_report(self, run_id: str) -> EvalReport | None:
        pool = await self._get_pool()
        row = await pool.fetchrow("SELECT * FROM eval_reports WHERE run_id = $1", run_id)
        if not row:
            return None
        data = dict(row)
        data["app_config"] = json.loads(data["app_config"])
        data["aggregated_scores"] = json.loads(data["aggregated_scores"])
        data["regression_report"] = (
            json.loads(data["regression_report"]) if data["regression_report"] else None
        )
        return EvalReport(**data)
