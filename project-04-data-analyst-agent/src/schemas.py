from pydantic import BaseModel


class CodeRun(BaseModel):
    step: str
    code: str
    stdout: str
    stderr: str
    success: bool
    attempt: int


class ChartResult(BaseModel):
    path: str
    description: str


class ChartSummary(BaseModel):
    filename: str
    description: str


class AnalysisPlan(BaseModel):
    steps: list[str]


class GeneratedCode(BaseModel):
    code: str
    explanation: str


class StepVerdict(BaseModel):
    analysis_complete: bool
    observation: str


class AnalysisReport(BaseModel):
    question: str
    answer: str
    key_findings: list[str]
    charts: list[ChartSummary]
    caveats: list[str]
