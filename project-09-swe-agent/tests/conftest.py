from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.models import (
    FileInfo,
    ImplementationPlan,
    Issue,
    Patch,
    PlanStep,
    SWETestRun,
)


@pytest.fixture
def sample_issue() -> Issue:
    return Issue(
        number=42,
        title="Fix division by zero in calculator",
        body="The `divide` function crashes when denominator is 0. Add a guard.",
        repo_full_name="acme/calculator",
        url="https://github.com/acme/calculator/issues/42",
        labels=["bug"],
    )


@pytest.fixture
def sample_plan(sample_issue) -> ImplementationPlan:
    return ImplementationPlan(
        steps=[
            PlanStep(
                step_number=1,
                description="Add zero-division guard in divide()",
                file_path="src/calculator.py",
                action="modify",
                rationale="Prevents ZeroDivisionError crash",
            )
        ],
        affected_files=["src/calculator.py"],
        test_strategy="Run existing unit tests; add test for denominator=0",
        estimated_complexity="trivial",
    )


@pytest.fixture
def sample_test_run() -> SWETestRun:
    return SWETestRun(
        iteration=0,
        exit_code=0,
        passed=5,
        failed=0,
        duration_ms=320,
        raw_output="5 passed in 0.32s",
    )


@pytest.fixture
def failing_test_run() -> SWETestRun:
    return SWETestRun(
        iteration=1,
        exit_code=1,
        passed=4,
        failed=1,
        errors=["FAILED tests/test_calc.py::test_divide_zero - ZeroDivisionError"],
        duration_ms=280,
        raw_output="FAILED tests/test_calc.py::test_divide_zero - ZeroDivisionError\n1 failed",
    )


@pytest.fixture
def sample_patch() -> Patch:
    return Patch(
        iteration=0,
        file_path="src/calculator.py",
        unified_diff="--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -3,4 +3,6 @@\n def divide(a, b):\n+    if b == 0:\n+        raise ValueError('denominator cannot be zero')\n     return a / b\n",
        description="Add zero-division guard",
    )


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def sample_python_file(tmp_workspace: Path) -> Path:
    calc = tmp_workspace / "src" / "calculator.py"
    calc.write_text(
        "def add(a, b):\n    return a + b\n\ndef divide(a, b):\n    return a / b\n"
    )
    return calc
