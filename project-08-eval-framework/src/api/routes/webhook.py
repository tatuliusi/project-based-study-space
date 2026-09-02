from __future__ import annotations

import asyncio

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.routes.runs import _execute_run
from src.api.schemas import WebhookPayload
from src.models import AppConfig, EvalRun

router = APIRouter(prefix="/webhook", tags=["webhook"])

_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 300.0


@router.post("/github")
async def github_webhook(
    payload: WebhookPayload,
    request: Request,
    x_github_event: str | None = Header(default=None),
) -> JSONResponse:
    if x_github_event not in ("push", "pull_request", None):
        return JSONResponse({"skipped": True}, status_code=200)

    db = request.app.state.db

    dataset_id = payload.dataset_id
    app_config = payload.app_config

    if not dataset_id or not app_config:
        raise HTTPException(
            status_code=422,
            detail="dataset_id and app_config are required in webhook payload",
        )

    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"dataset {dataset_id} not found")

    run = EvalRun(dataset_id=dataset_id, app_config=app_config)
    await db.save_run(run)

    await _execute_run(run, dataset.samples, db)

    report = await db.get_report(run.id)
    if not report:
        raise HTTPException(status_code=500, detail="eval run produced no report")

    regression = report.regression_report
    if regression and not regression.passed:
        regressions = [r.model_dump() for r in regression.regressions]
        return JSONResponse(
            {
                "run_id": run.id,
                "passed": False,
                "regressions": regressions,
                "sha": payload.sha,
            },
            status_code=422,
        )

    return JSONResponse(
        {"run_id": run.id, "passed": True, "sha": payload.sha},
        status_code=200,
    )
