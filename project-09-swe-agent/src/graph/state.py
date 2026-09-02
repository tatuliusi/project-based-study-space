from __future__ import annotations

from typing import TypedDict

from ..models import FileInfo, ImplementationPlan, Issue, Patch, TestRun


class SWEState(TypedDict, total=False):
    task_id: str
    issue_url: str
    repo_path: str
    issue: Issue
    repo_map: dict[str, FileInfo]
    plan: ImplementationPlan | None
    patches: list[Patch]
    test_results: list[TestRun]
    iteration: int
    max_iterations: int
    approved: bool
    pr_url: str | None
    error: str | None
