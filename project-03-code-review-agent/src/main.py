import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root.parent / ".env")  # workspace root (shared API keys)
load_dotenv(_project_root / ".env")         # project-level overrides

from src.graph import review_pr  # noqa: E402
from src.schemas import CodeReview, Finding  # noqa: E402

_SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}
_VERDICT_LABELS = {
    "request_changes": "REQUEST CHANGES",
    "comment": "COMMENT",
    "approve": "APPROVE",
}


def _print_findings(label: str, findings: list[Finding]) -> None:
    if not findings:
        return
    print(f"\n{label} ({len(findings)}):")
    for f in sorted(findings, key=lambda x: _SEVERITY_ORDER[x.severity]):
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"  [{f.severity.upper()}] {loc}")
        print(f"    {f.description}")
        print(f"    -> {f.suggestion}")


def _print_review(pr_url: str, review: CodeReview, security: list, logic: list, style: list) -> None:
    width = 60
    print("=" * width)
    print(f"CODE REVIEW — {pr_url}")
    print("=" * width)
    print(f"Verdict: {_VERDICT_LABELS[review.verdict]}")
    print(f"\nSummary:\n{review.summary}")

    if review.priority_issues:
        print(f"\nPRIORITY ISSUES ({len(review.priority_issues)}):")
        for f in review.priority_issues:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  [{f.severity.upper()}] {loc}: {f.description}")
            print(f"    -> {f.suggestion}")

    _print_findings("SECURITY", security)
    _print_findings("LOGIC", logic)
    _print_findings("STYLE", style)
    print("=" * width)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated code review agent — points at a GitHub PR and outputs a structured review."
    )
    parser.add_argument(
        "--pr",
        required=True,
        help="PR reference: owner/repo/number or full GitHub PR URL",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )
    args = parser.parse_args()

    print(f"Fetching and reviewing {args.pr} ...")

    from src.graph import build_graph
    from src.state import ReviewState

    app = build_graph()
    result = app.invoke({
        "pr_url": args.pr,
        "diff": "",
        "file_summaries": [],
        "security_findings": [],
        "logic_findings": [],
        "style_findings": [],
        "final_review": None,
    })

    review: CodeReview = result["final_review"]

    if args.json:
        print(review.model_dump_json(indent=2))
        return

    _print_review(
        args.pr,
        review,
        result.get("security_findings", []),
        result.get("logic_findings", []),
        result.get("style_findings", []),
    )


if __name__ == "__main__":
    main()
