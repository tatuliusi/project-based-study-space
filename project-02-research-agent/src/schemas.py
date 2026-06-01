from pydantic import BaseModel, Field


class CoverageVerdict(BaseModel):
    sufficient: bool
    gaps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Citation(BaseModel):
    title: str
    url: str
    snippet: str


class Finding(BaseModel):
    point: str
    sources: list[Citation]


class ResearchReport(BaseModel):
    title: str
    summary: str
    key_findings: list[Finding]
    sources: list[Citation]
    conclusion: str
