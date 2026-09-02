from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    ApproveResponse,
    SubmitTaskRequest,
    SubmitTaskResponse,
    TaskDiffResponse,
    TaskPlanResponse,
    TaskPRResponse,
    TaskStatusResponse,
)


def test_submit_task_request():
    req = SubmitTaskRequest(issue_url="https://github.com/a/b/issues/1")
    assert req.issue_url == "https://github.com/a/b/issues/1"


def test_submit_task_response():
    resp = SubmitTaskResponse(task_id="abc-123")
    assert resp.task_id == "abc-123"


def test_task_status_response_defaults():
    resp = TaskStatusResponse(
        id="t1",
        issue_url="https://github.com/a/b/issues/1",
        status="running",
        current_step="explore_repo",
    )
    assert resp.pr_url is None
    assert resp.error is None


def test_task_status_response_full():
    resp = TaskStatusResponse(
        id="t1",
        issue_url="https://github.com/a/b/issues/1",
        status="done",
        current_step="open_pr",
        pr_url="https://github.com/a/b/pull/5",
        error=None,
    )
    assert resp.pr_url is not None


def test_task_plan_response_no_plan():
    resp = TaskPlanResponse(task_id="t1")
    assert resp.plan is None


def test_task_diff_response():
    resp = TaskDiffResponse(task_id="t1", diff="--- a\n+++ b\n@@ ... @@\n+fix")
    assert "fix" in resp.diff


def test_approve_response():
    resp = ApproveResponse(status="approved")
    assert resp.status == "approved"


def test_task_pr_response_no_url():
    resp = TaskPRResponse(task_id="t1")
    assert resp.pr_url is None


def test_task_pr_response_with_url():
    resp = TaskPRResponse(task_id="t1", pr_url="https://github.com/a/b/pull/7")
    assert resp.pr_url == "https://github.com/a/b/pull/7"
