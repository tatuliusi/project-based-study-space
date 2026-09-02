from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from src.api.schemas import CreateRunRequest, RunResponse
from src.graph.pipeline import eval_graph
from src.models import EvalReport, EvalRun

router = APIRouter(prefix="/runs", tags=["runs"])


async def _execute_run(run: EvalRun, samples: list, db) -> None:
    await db.update_run_status(run.id, "running")
    try:
        initial_state = {
            "run_id": run.id,
            "dataset_id": run.dataset_id,
            "app_config": run.app_config,
            "metric_set": [],
            "baseline_run_id": run.baseline_run_id,
            "samples": samples,
            "sample_results": [],
            "aggregated_scores": None,
            "regression_report": None,
            "final_report": None,
        }

        dataset = await db.get_dataset(run.dataset_id)
        if dataset:
            initial_state["metric_set"] = dataset.metric_set

        final_state = await eval_graph.ainvoke(initial_state)
        report: EvalReport | None = final_state.get("final_report")
        if report:
            await db.save_report(report)
        await db.update_run_status(run.id, "completed")
    except Exception:
        await db.update_run_status(run.id, "failed")
        raise


@router.post("", response_model=RunResponse, status_code=202)
async def create_run(
    req: CreateRunRequest, request: Request, background_tasks: BackgroundTasks
) -> RunResponse:
    db = request.app.state.db
    dataset = await db.get_dataset(req.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")

    run = EvalRun(
        dataset_id=req.dataset_id,
        app_config=req.app_config,
        baseline_run_id=req.baseline_run_id,
    )
    await db.save_run(run)
    background_tasks.add_task(_execute_run, run, dataset.samples, db)
    return RunResponse(run=run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, request: Request) -> RunResponse:
    db = request.app.state.db
    report = await db.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="run not found or not completed")
    dummy_run = EvalRun(
        id=run_id,
        dataset_id=report.dataset_id,
        app_config=report.app_config,
        status="completed",
    )
    return RunResponse(run=dummy_run, report=report)
