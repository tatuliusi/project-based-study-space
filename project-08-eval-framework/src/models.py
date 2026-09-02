from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _uid() -> str:
    return str(uuid4())


class AppConfig(BaseModel):
    app_id: str
    model: str
    prompt_version: str = "v1"


class EvalSample(BaseModel):
    id: str = Field(default_factory=_uid)
    input: str
    expected_output: str | None = None
    context: list[str] | None = None


class SampleResult(BaseModel):
    sample_id: str
    actual_output: str
    latency_ms: int
    scores: dict[str, float] = Field(default_factory=dict)
    judge_rationale: dict[str, str] = Field(default_factory=dict)


class MetricStats(BaseModel):
    mean: float
    min: float
    max: float
    std: float
    count: int


class Regression(BaseModel):
    metric: str
    delta: float
    severity: Literal["minor", "major", "critical"]


class RegressionReport(BaseModel):
    regressions: list[Regression] = Field(default_factory=list)
    passed: bool


class EvalReport(BaseModel):
    run_id: str
    dataset_id: str
    app_config: AppConfig
    aggregated_scores: dict[str, MetricStats]
    regression_report: RegressionReport | None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Dataset(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    description: str = ""
    metric_set: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    samples: list[EvalSample] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvalRun(BaseModel):
    id: str = Field(default_factory=_uid)
    dataset_id: str
    app_config: AppConfig
    baseline_run_id: str | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
