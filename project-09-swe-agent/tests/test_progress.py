from __future__ import annotations

import time

import pytest

from src.progress import ProgressTracker, StepEvent


def test_tracker_initial_state():
    tracker = ProgressTracker(task_id="t1")
    assert tracker.current_step() == "pending"
    assert tracker.elapsed_seconds() == 0.0
    assert tracker.iteration_count() == 0


def test_tracker_records_steps():
    tracker = ProgressTracker(task_id="t1")
    tracker.record("analyze_issue", {"issue": "..."})
    tracker.record("explore_repo", {"repo_map": {}})
    assert tracker.current_step() == "explore_repo"
    assert len(tracker.events) == 2


def test_tracker_records_output_keys():
    tracker = ProgressTracker(task_id="t1")
    tracker.record("create_plan", {"plan": "...", "extra": 1})
    event = tracker.events[-1]
    assert "plan" in event.output_keys
    assert "extra" in event.output_keys


def test_tracker_iteration_count():
    tracker = ProgressTracker(task_id="t1")
    tracker.record("run_tests", {"test_results": []}, iteration=1)
    tracker.record("analyze_failures", {"error": "..."}, iteration=1)
    tracker.record("patch", {"patches": []}, iteration=1)
    tracker.record("run_tests", {"test_results": []}, iteration=2)
    assert tracker.iteration_count() == 2


def test_tracker_to_dict():
    tracker = ProgressTracker(task_id="abc")
    tracker.record("analyze_issue", {"issue": "x"})
    d = tracker.to_dict()
    assert d["task_id"] == "abc"
    assert d["current_step"] == "analyze_issue"
    assert len(d["steps"]) == 1
    assert "timestamp" in d["steps"][0]


def test_tracker_elapsed_seconds():
    tracker = ProgressTracker(task_id="t1")
    tracker.record("start", {})
    time.sleep(0.05)
    tracker.record("end", {})
    assert tracker.elapsed_seconds() >= 0.04


def test_step_event_defaults():
    event = StepEvent(node="analyze_issue")
    assert event.output_keys == []
    assert event.iteration == 0
    assert event.timestamp is not None
