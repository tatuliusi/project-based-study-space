from typing_extensions import TypedDict

from src.schemas import AnalysisReport, ChartResult, CodeRun


class AnalysisState(TypedDict):
    file_path: str
    question: str
    dataframe_info: str
    analysis_plan: list[str]
    current_step_index: int
    fix_attempts: int
    code_history: list[CodeRun]
    charts: list[ChartResult]
    iteration: int
    report: AnalysisReport | None
