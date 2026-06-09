import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class Source(BaseModel):
    url: str
    title: str
    snippet: str
    domain_credibility: float = Field(default=0.5, ge=0.0, le=1.0)


class Finding(BaseModel):
    sub_topic: str
    summary: str
    sources: list[Source] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class FactCheckResult(BaseModel):
    claim: str
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_sources: list[str] = Field(default_factory=list)


class ReportSection(BaseModel):
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)


class Report(BaseModel):
    job_id: str
    topic: str
    executive_summary: str
    sections: list[ReportSection]
    bibliography: list[Source]
    confidence_score: float = Field(ge=0.0, le=1.0)


class PipelineState(TypedDict):
    job_id: str
    topic: str
    sub_topics: list[str]
    findings: Annotated[list[Finding], operator.add]
    fact_check_results: list[FactCheckResult]
    report: Report | None
    artifact_url: str | None
    status: Literal["running", "done", "failed"]
    error: str | None


class BranchState(TypedDict):
    sub_topic: str
