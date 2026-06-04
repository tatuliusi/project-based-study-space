import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root.parent / ".env")
load_dotenv(_project_root / ".env")

from langgraph.types import Command  # noqa: E402

from src.graph import build_graph  # noqa: E402
from src.schemas import AnalysisReport  # noqa: E402
from src.state import AnalysisState  # noqa: E402


def _get_interrupt_steps(app, config: dict) -> list[str] | None:
    snapshot = app.get_state(config)
    for task in snapshot.tasks:
        if task.interrupts:
            val = task.interrupts[0].value
            if isinstance(val, dict) and "steps" in val:
                return val["steps"]
    return None


def _prompt_plan_approval(steps: list[str]) -> list[str]:
    print("\nAnalysis plan:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print("\nApprove this plan? [y] to accept, or paste a JSON list to replace steps.")
    user_input = input("> ").strip()
    if not user_input or user_input.lower() in ("y", "yes"):
        return steps
    try:
        edited = json.loads(user_input)
        if isinstance(edited, list) and all(isinstance(s, str) for s in edited):
            return edited
    except json.JSONDecodeError:
        pass
    print("Could not parse input — using original plan.")
    return steps


def _print_report(report: AnalysisReport) -> None:
    width = 70
    print("\n" + "=" * width)
    print("ANALYSIS REPORT")
    print("=" * width)
    print(f"Question: {report.question}")
    print(f"\nAnswer:\n{report.answer}")
    if report.key_findings:
        print(f"\nKey Findings:")
        for finding in report.key_findings:
            print(f"  - {finding}")
    if report.charts:
        print(f"\nCharts:")
        for chart in report.charts:
            print(f"  - {chart.filename}: {chart.description}")
    if report.caveats:
        print(f"\nCaveats:")
        for caveat in report.caveats:
            print(f"  - {caveat}")
    print("=" * width)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous data analyst — give it a CSV and a question."
    )
    parser.add_argument("--file", required=True, help="Path to the CSV file")
    parser.add_argument("--question", required=True, help="The analysis question to answer")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    parser.add_argument("--yes", action="store_true", help="Auto-approve the analysis plan (no HITL prompt)")
    args = parser.parse_args()

    file_path = str(Path(args.file).resolve())
    if not Path(file_path).exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    app = build_graph()
    config = {"configurable": {"thread_id": "1"}}
    initial_state: AnalysisState = {
        "file_path": file_path,
        "question": args.question,
        "dataframe_info": "",
        "analysis_plan": [],
        "current_step_index": 0,
        "fix_attempts": 0,
        "code_history": [],
        "charts": [],
        "iteration": 0,
        "report": None,
    }

    print(f"Loading {args.file} ...")
    app.invoke(initial_state, config=config)

    steps = _get_interrupt_steps(app, config)
    if steps is not None:
        if args.yes:
            approved = steps
        else:
            approved = _prompt_plan_approval(steps)
        print(f"\nRunning {len(approved)} analysis steps ...")
        result = app.invoke(Command(resume=approved), config=config)
    else:
        result = app.get_state(config).values

    report: AnalysisReport | None = result.get("report")
    if report is None:
        print("No report generated.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        _print_report(report)

    charts = result.get("charts", [])
    if charts:
        print(f"\nCharts saved to: {Path(file_path).parent / 'charts'}/")


if __name__ == "__main__":
    main()
