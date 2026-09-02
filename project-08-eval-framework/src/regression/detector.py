from __future__ import annotations

from typing import Literal

from src.config import settings
from src.models import MetricStats, Regression, RegressionReport


def _classify_severity(delta: float) -> Literal["minor", "major", "critical"]:
    if delta < -0.2:
        return "critical"
    if delta < -0.1:
        return "major"
    return "minor"


def detect_regressions(state: dict) -> dict:
    current: dict[str, MetricStats] = state.get("aggregated_scores") or {}
    baseline: dict[str, MetricStats] = state.get("baseline_scores") or {}

    if not baseline:
        return {"regression_report": RegressionReport(passed=True)}

    regressions: list[Regression] = []

    for metric, stats in current.items():
        if stats.mean < settings.absolute_floor_correctness and metric == "correctness":
            regressions.append(
                Regression(
                    metric=metric,
                    delta=stats.mean - settings.absolute_floor_correctness,
                    severity="critical",
                )
            )
            continue

        if metric not in baseline:
            continue

        delta = stats.mean - baseline[metric].mean
        if delta < -settings.regression_threshold:
            regressions.append(
                Regression(
                    metric=metric,
                    delta=delta,
                    severity=_classify_severity(delta),
                )
            )

    return {
        "regression_report": RegressionReport(
            regressions=regressions,
            passed=len(regressions) == 0,
        )
    }
