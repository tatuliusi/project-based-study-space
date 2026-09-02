from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class SubmitTaskRequest(BaseModel):
    issue_url: str


class SubmitTaskResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    id: str
    issue_url: str
    status: str
    current_step: str
    pr_url: str | None = None
    error: str | None = None


class TaskPlanResponse(BaseModel):
    task_id: str
    plan: dict | None = None


class TaskDiffResponse(BaseModel):
    task_id: str
    diff: str


class ApproveResponse(BaseModel):
    status: str


class TaskPRResponse(BaseModel):
    task_id: str
    pr_url: str | None = None
