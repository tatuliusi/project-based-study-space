from __future__ import annotations

import pytest

from src.graph.state import SWEState
from src.models import Issue, Patch, TestRun


def test_swe_state_is_dict_subtype():
    state: SWEState = {
        "task_id": "abc",
        "issue_url": "https://github.com/a/b/issues/1",
        "repo_path": "/tmp/repo",
        "patches": [],
        "test_results": [],
        "iteration": 0,
        "max_iterations": 5,
        "approved": False,
        "pr_url": None,
        "error": None,
    }
    assert state["task_id"] == "abc"
    assert state["iteration"] == 0


def test_swe_state_optional_fields():
    state: SWEState = {
        "task_id": "xyz",
        "issue_url": "https://github.com/a/b/issues/2",
    }
    assert state.get("plan") is None
    assert state.get("pr_url") is None


def test_swe_state_accepts_issue(sample_issue):
    state: SWEState = {
        "task_id": "t1",
        "issue_url": sample_issue.url,
        "issue": sample_issue,
    }
    assert state["issue"].number == 42


def test_swe_state_accumulates_test_results(sample_test_run, failing_test_run):
    results: list[TestRun] = [sample_test_run, failing_test_run]
    state: SWEState = {
        "task_id": "t2",
        "issue_url": "u",
        "test_results": results,
        "iteration": 2,
    }
    assert len(state["test_results"]) == 2
    assert state["test_results"][1].failed == 1


def test_swe_state_patches_list(sample_patch):
    state: SWEState = {
        "task_id": "t3",
        "issue_url": "u",
        "patches": [sample_patch],
    }
    assert len(state["patches"]) == 1
    assert state["patches"][0].file_path == "src/calculator.py"
