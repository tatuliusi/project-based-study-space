from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.nodes import aggregate_results
from src.models import AppConfig, EvalSample, MetricStats, SampleResult


def _make_result(sample_id: str, **scores) -> SampleResult:
    return SampleResult(
        sample_id=sample_id,
        actual_output="test output",
        latency_ms=100,
        scores=scores,
    )


class TestAggregateResults:
    def test_single_result(self):
        state = {
            "sample_results": [_make_result("s1", correctness=0.8, faithfulness=0.9)],
        }
        result = aggregate_results(state)
        scores = result["aggregated_scores"]
        assert "correctness" in scores
        assert "faithfulness" in scores
        assert scores["correctness"].mean == pytest.approx(0.8)
        assert scores["faithfulness"].mean == pytest.approx(0.9)

    def test_multiple_results_mean(self):
        state = {
            "sample_results": [
                _make_result("s1", correctness=0.8),
                _make_result("s2", correctness=0.6),
            ],
        }
        result = aggregate_results(state)
        assert result["aggregated_scores"]["correctness"].mean == pytest.approx(0.7)

    def test_missing_metric_skipped(self):
        state = {
            "sample_results": [
                _make_result("s1", correctness=0.8),
                _make_result("s2", faithfulness=0.9),
            ],
        }
        result = aggregate_results(state)
        scores = result["aggregated_scores"]
        assert scores["correctness"].count == 1
        assert scores["faithfulness"].count == 1

    def test_empty_results(self):
        state = {"sample_results": []}
        result = aggregate_results(state)
        assert result["aggregated_scores"] == {}

    def test_stats_fields_populated(self):
        state = {
            "sample_results": [
                _make_result("s1", correctness=0.6),
                _make_result("s2", correctness=0.8),
                _make_result("s3", correctness=1.0),
            ],
        }
        result = aggregate_results(state)
        stats: MetricStats = result["aggregated_scores"]["correctness"]
        assert stats.min == pytest.approx(0.6)
        assert stats.max == pytest.approx(1.0)
        assert stats.count == 3
        assert stats.std > 0
