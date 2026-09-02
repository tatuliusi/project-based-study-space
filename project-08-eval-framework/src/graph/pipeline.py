from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    aggregate_results,
    build_report,
    evaluate_sample,
    fan_out_samples,
)
from src.graph.state import EvalRunState, SampleEvalState
from src.regression.detector import detect_regressions


def _maybe_detect_regressions(state: EvalRunState) -> dict:
    if not state.get("baseline_run_id") or not state.get("aggregated_scores"):
        from src.models import RegressionReport
        return {"regression_report": RegressionReport(passed=True)}
    return detect_regressions(state)


def build_eval_graph() -> StateGraph:
    g = StateGraph(EvalRunState)

    g.add_node("evaluate_sample", evaluate_sample)
    g.add_node("aggregate_results", aggregate_results)
    g.add_node("detect_regressions", _maybe_detect_regressions)
    g.add_node("build_report", build_report)

    g.add_conditional_edges(START, fan_out_samples, ["evaluate_sample"])
    g.add_edge("evaluate_sample", "aggregate_results")
    g.add_edge("aggregate_results", "detect_regressions")
    g.add_edge("detect_regressions", "build_report")
    g.add_edge("build_report", END)

    return g.compile()


eval_graph = build_eval_graph()
