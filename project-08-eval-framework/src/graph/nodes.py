from __future__ import annotations

import asyncio
import math
import statistics
import time

from langgraph.types import Send

from src.config import settings
from src.graph.state import EvalRunState, SampleEvalState
from src.metrics.deterministic import DETERMINISTIC_METRICS
from src.metrics.llm_judge import LLM_METRICS, judge
from src.models import (
    AppConfig,
    EvalReport,
    EvalSample,
    MetricStats,
    RegressionReport,
    SampleResult,
)
from src.services.app_runner import run_app


def fan_out_samples(state: EvalRunState) -> list[Send]:
    return [
        Send(
            "evaluate_sample",
            SampleEvalState(
                run_id=state["run_id"],
                app_config=state["app_config"],
                metric_set=state["metric_set"],
                sample=sample,
            ),
        )
        for sample in state["samples"]
    ]


async def evaluate_sample(state: SampleEvalState) -> dict:
    sample: EvalSample = state["sample"]
    app_config: AppConfig = state["app_config"]
    metric_set: list[str] = state["metric_set"]

    repeat_scores: list[dict[str, float]] = []
    repeat_rationales: list[dict[str, str]] = []
    latencies: list[int] = []

    for _ in range(settings.sample_repeats):
        t0 = time.monotonic()
        actual = await run_app(app_config, sample.input, sample.context)
        latency_ms = int((time.monotonic() - t0) * 1000)
        latencies.append(latency_ms)

        scores: dict[str, float] = {}
        rationales: dict[str, str] = {}

        for metric in metric_set:
            if metric in DETERMINISTIC_METRICS and sample.expected_output:
                fn = DETERMINISTIC_METRICS[metric]
                scores[metric] = fn(actual, sample.expected_output)
                rationales[metric] = "deterministic"
            elif metric in LLM_METRICS:
                out = await judge(
                    metric_name=metric,
                    input_text=sample.input,
                    actual=actual,
                    expected=sample.expected_output,
                    context=sample.context,
                )
                scores[metric] = out.score
                rationales[metric] = out.rationale

        repeat_scores.append(scores)
        repeat_rationales.append(rationales)

    averaged_scores = {
        m: statistics.mean(r[m] for r in repeat_scores if m in r)
        for m in metric_set
    }
    last_rationales = repeat_rationales[-1] if repeat_rationales else {}

    result = SampleResult(
        sample_id=sample.id,
        actual_output=actual,
        latency_ms=int(statistics.mean(latencies)),
        scores=averaged_scores,
        judge_rationale=last_rationales,
    )
    return {"sample_results": [result]}


def aggregate_results(state: EvalRunState) -> dict:
    results = state["sample_results"]
    all_metrics: set[str] = set()
    for r in results:
        all_metrics.update(r.scores.keys())

    aggregated: dict[str, MetricStats] = {}
    for metric in all_metrics:
        vals = [r.scores[metric] for r in results if metric in r.scores]
        if not vals:
            continue
        aggregated[metric] = MetricStats(
            mean=statistics.mean(vals),
            min=min(vals),
            max=max(vals),
            std=statistics.stdev(vals) if len(vals) > 1 else 0.0,
            count=len(vals),
        )

    return {"aggregated_scores": aggregated}


def build_report(state: EvalRunState) -> dict:
    report = EvalReport(
        run_id=state["run_id"],
        dataset_id=state["dataset_id"],
        app_config=state["app_config"],
        aggregated_scores=state["aggregated_scores"] or {},
        regression_report=state.get("regression_report"),
    )
    return {"final_report": report}
