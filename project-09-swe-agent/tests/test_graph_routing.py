from __future__ import annotations

import pytest

from src.graph.nodes import should_iterate
from src.models import SWETestRun


def _state_with_results(test_results, iteration=1, max_iterations=5):
    return {
        "task_id": "t",
        "issue_url": "u",
        "test_results": test_results,
        "iteration": iteration,
        "max_iterations": max_iterations,
    }


def test_should_iterate_no_results():
    state = _state_with_results([])
    assert should_iterate(state) == "iterate"


def test_should_iterate_tests_pass(sample_test_run):
    state = _state_with_results([sample_test_run], iteration=1)
    assert should_iterate(state) == "approve"


def test_should_iterate_tests_fail(failing_test_run):
    state = _state_with_results([failing_test_run], iteration=1)
    assert should_iterate(state) == "iterate"


def test_should_iterate_max_reached(failing_test_run):
    state = _state_with_results([failing_test_run], iteration=5, max_iterations=5)
    assert should_iterate(state) == "approve"


def test_should_iterate_max_exceeded(failing_test_run):
    state = _state_with_results([failing_test_run], iteration=10, max_iterations=5)
    assert should_iterate(state) == "approve"


def test_should_iterate_uses_last_result():
    passing = SWETestRun(iteration=0, exit_code=0, passed=3, failed=0, duration_ms=100)
    failing = SWETestRun(iteration=1, exit_code=1, passed=2, failed=1, duration_ms=200)
    state = _state_with_results([passing, failing], iteration=2)
    assert should_iterate(state) == "iterate"


def test_should_iterate_exits_on_pass_after_fail():
    failing = SWETestRun(iteration=0, exit_code=1, passed=0, failed=2, duration_ms=100)
    passing = SWETestRun(iteration=1, exit_code=0, passed=2, failed=0, duration_ms=100)
    state = _state_with_results([failing, passing], iteration=2)
    assert should_iterate(state) == "approve"
