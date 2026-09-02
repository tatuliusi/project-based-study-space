from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import (
    FileInfo,
    ImplementationPlan,
    Issue,
    Patch,
    PlanStep,
    TaskRecord,
    TestRun,
)


def test_issue_defaults():
    issue = Issue(
        number=1,
        title="t",
        body="b",
        repo_full_name="a/b",
        url="https://github.com/a/b/issues/1",
    )
    assert issue.labels == []


def test_issue_roundtrip(sample_issue):
    data = sample_issue.model_dump()
    restored = Issue.model_validate(data)
    assert restored.number == sample_issue.number
    assert restored.labels == ["bug"]


def test_plan_step_literal_validation():
    with pytest.raises(ValidationError):
        PlanStep(
            step_number=1,
            description="d",
            file_path="f.py",
            action="unsupported_action",
            rationale="r",
        )


def test_plan_step_valid_actions():
    for action in ("create", "modify", "delete"):
        step = PlanStep(
            step_number=1,
            description="d",
            file_path="f.py",
            action=action,
            rationale="r",
        )
        assert step.action == action


def test_implementation_plan_roundtrip(sample_plan):
    data = sample_plan.model_dump()
    restored = ImplementationPlan.model_validate(data)
    assert len(restored.steps) == 1
    assert restored.estimated_complexity == "trivial"


def test_test_run_defaults():
    tr = TestRun(iteration=0, exit_code=0, passed=3, failed=0, duration_ms=100)
    assert tr.errors == []
    assert tr.raw_output == ""


def test_test_run_failed(failing_test_run):
    assert failing_test_run.exit_code == 1
    assert failing_test_run.failed == 1
    assert len(failing_test_run.errors) == 1


def test_patch_roundtrip(sample_patch):
    data = sample_patch.model_dump()
    restored = Patch.model_validate(data)
    assert restored.file_path == sample_patch.file_path


def test_task_record_status_literal():
    with pytest.raises(ValidationError):
        TaskRecord(id="x", issue_url="u", status="invalid_status")


def test_task_record_valid():
    record = TaskRecord(id="abc", issue_url="https://github.com/a/b/issues/1", status="queued")
    assert record.pr_url is None
    assert record.error is None


def test_file_info_defaults():
    fi = FileInfo(path="src/foo.py", size_bytes=100, language="python")
    assert fi.symbols == []
    assert fi.summary == ""
