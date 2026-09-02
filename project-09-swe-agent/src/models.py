from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Issue(BaseModel):
    number: int
    title: str
    body: str
    repo_full_name: str
    url: str
    labels: list[str] = Field(default_factory=list)


class FileInfo(BaseModel):
    path: str
    size_bytes: int
    language: str
    symbols: list[str] = Field(default_factory=list)
    summary: str = ""


class PlanStep(BaseModel):
    step_number: int
    description: str
    file_path: str
    action: Literal["create", "modify", "delete"]
    rationale: str


class ImplementationPlan(BaseModel):
    steps: list[PlanStep]
    affected_files: list[str]
    test_strategy: str
    estimated_complexity: Literal["trivial", "small", "medium", "large"]


class Patch(BaseModel):
    iteration: int
    file_path: str
    unified_diff: str
    description: str


class TestRun(BaseModel):
    iteration: int
    exit_code: int
    passed: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    duration_ms: int
    raw_output: str = ""


class SearchResult(BaseModel):
    file_path: str
    line_number: int
    line_content: str
    context: str = ""


class CommandResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class PatchResult(BaseModel):
    success: bool
    file_path: str
    error: str = ""


class TaskRecord(BaseModel):
    id: str
    issue_url: str
    status: Literal["queued", "running", "awaiting_approval", "approved", "done", "failed"]
    current_step: str = ""
    pr_url: str | None = None
    error: str | None = None
