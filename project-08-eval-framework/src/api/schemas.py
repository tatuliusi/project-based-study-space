from __future__ import annotations

from pydantic import BaseModel, Field

from src.models import AppConfig, EvalReport, EvalRun, EvalSample, RegressionReport


class CreateDatasetRequest(BaseModel):
    name: str
    description: str = ""
    metric_set: list[str]
    samples: list[EvalSample] = Field(default_factory=list)


class AddSamplesRequest(BaseModel):
    samples: list[EvalSample]


class CreateRunRequest(BaseModel):
    dataset_id: str
    app_config: AppConfig
    baseline_run_id: str | None = None


class RunResponse(BaseModel):
    run: EvalRun
    report: EvalReport | None = None


class WebhookPayload(BaseModel):
    repo: str
    sha: str
    dataset_id: str | None = None
    app_config: AppConfig | None = None
