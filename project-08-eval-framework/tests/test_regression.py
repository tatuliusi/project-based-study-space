from __future__ import annotations

import pytest

from src.models import MetricStats, Regression, RegressionReport
from src.regression.detector import _classify_severity, detect_regressions


def _stats(mean: float, count: int = 10) -> MetricStats:
    return MetricStats(mean=mean, min=mean - 0.1, max=mean + 0.1, std=0.05, count=count)


class TestClassifySeverity:
    def test_minor(self):
        assert _classify_severity(-0.06) == "minor"

    def test_major(self):
        assert _classify_severity(-0.15) == "major"

    def test_critical(self):
        assert _classify_severity(-0.25) == "critical"


class TestDetectRegressions:
    def test_no_baseline_returns_passed(self):
        state = {"aggregated_scores": {"correctness": _stats(0.9)}, "baseline_scores": {}}
        result = detect_regressions(state)
        assert result["regression_report"].passed is True

    def test_no_regression_when_scores_hold(self):
        state = {
            "aggregated_scores": {"correctness": _stats(0.9)},
            "baseline_scores": {"correctness": _stats(0.88)},
        }
        result = detect_regressions(state)
        assert result["regression_report"].passed is True

    def test_regression_detected_on_drop(self):
        state = {
            "aggregated_scores": {"correctness": _stats(0.75)},
            "baseline_scores": {"correctness": _stats(0.85)},
        }
        result = detect_regressions(state)
        report: RegressionReport = result["regression_report"]
        assert report.passed is False
        assert len(report.regressions) == 1
        assert report.regressions[0].metric == "correctness"

    def test_absolute_floor_triggers_regression(self):
        state = {
            "aggregated_scores": {"correctness": _stats(0.65)},
            "baseline_scores": {"correctness": _stats(0.66)},
        }
        result = detect_regressions(state)
        report: RegressionReport = result["regression_report"]
        assert report.passed is False
        assert report.regressions[0].severity == "critical"

    def test_multiple_regressions(self):
        state = {
            "aggregated_scores": {
                "answer_relevance": _stats(0.5),
                "faithfulness": _stats(0.5),
            },
            "baseline_scores": {
                "answer_relevance": _stats(0.9),
                "faithfulness": _stats(0.9),
            },
        }
        result = detect_regressions(state)
        assert result["regression_report"].passed is False
        assert len(result["regression_report"].regressions) == 2
