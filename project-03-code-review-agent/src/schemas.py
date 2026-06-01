from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    severity: Literal["critical", "major", "minor", "info"]
    file: str
    line: int | None = None
    description: str
    suggestion: str


class FileSummary(BaseModel):
    filename: str
    status: Literal["added", "modified", "removed"]
    patch: str


class AgentFindings(BaseModel):
    findings: list[Finding] = Field(default_factory=list)


class CodeReview(BaseModel):
    verdict: Literal["approve", "request_changes", "comment"]
    summary: str
    priority_issues: list[Finding]
