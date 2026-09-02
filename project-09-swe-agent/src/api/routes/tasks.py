from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ...services.postgres_service import get_task, get_task_state
from ...services.task_service import approve_task, submit_task
from ..schemas import (
    ApproveResponse,
    SubmitTaskRequest,
    SubmitTaskResponse,
    TaskDiffResponse,
    TaskPlanResponse,
    TaskPRResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=SubmitTaskResponse, status_code=201)
async def create_task(body: SubmitTaskRequest) -> SubmitTaskResponse:
    task_id = await submit_task(body.issue_url)
    return SubmitTaskResponse(task_id=task_id)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(
        id=task["id"],
        issue_url=task["issue_url"],
        status=task["status"],
        current_step=task["current_step"],
        pr_url=task.get("pr_url"),
        error=task.get("error"),
    )


@router.get("/{task_id}/plan", response_model=TaskPlanResponse)
async def get_task_plan(task_id: str) -> TaskPlanResponse:
    state = await get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="task not found or no state saved yet")
    plan = state.get("plan")
    return TaskPlanResponse(task_id=task_id, plan=plan)


@router.get("/{task_id}/diff", response_model=TaskDiffResponse)
async def get_task_diff(task_id: str) -> TaskDiffResponse:
    state = await get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="task not found")
    patches = state.get("patches", [])
    diff_text = "\n\n".join(
        f"# {p.get('file_path', '')}\n{p.get('unified_diff', '')}" for p in patches
    )
    return TaskDiffResponse(task_id=task_id, diff=diff_text)


@router.post("/{task_id}/approve", response_model=ApproveResponse)
async def approve_task_endpoint(task_id: str) -> ApproveResponse:
    result = await approve_task(task_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return ApproveResponse(status=result["status"])


@router.get("/{task_id}/pr", response_model=TaskPRResponse)
async def get_task_pr(task_id: str) -> TaskPRResponse:
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskPRResponse(task_id=task_id, pr_url=task.get("pr_url"))
