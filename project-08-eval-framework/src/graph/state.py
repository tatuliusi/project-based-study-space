from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from src.models import AppConfig, EvalReport, EvalSample, RegressionReport, SampleResult
from src.models import MetricStats


class EvalRunState(TypedDict):
    run_id: str
    dataset_id: str
    app_config: AppConfig
    metric_set: list[str]
    baseline_run_id: str | None
    samples: list[EvalSample]
    sample_results: Annotated[list[SampleResult], operator.add]
    aggregated_scores: dict[str, MetricStats] | None
    regression_report: RegressionReport | None
    final_report: EvalReport | None


class SampleEvalState(TypedDict):
    run_id: str
    app_config: AppConfig
    metric_set: list[str]
    sample: EvalSample
