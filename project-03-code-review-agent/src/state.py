from typing_extensions import TypedDict

from src.schemas import CodeReview, FileSummary, Finding


class ReviewState(TypedDict):
    pr_url: str
    diff: str
    file_summaries: list[FileSummary]
    security_findings: list[Finding]
    logic_findings: list[Finding]
    style_findings: list[Finding]
    final_review: CodeReview | None
