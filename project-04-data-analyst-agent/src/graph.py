from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes import (
    execute_code,
    fix_code,
    generate_code,
    generate_report,
    interpret_results,
    load_data,
    plan_analysis,
    _MAX_FIX_ATTEMPTS,
)
from src.state import AnalysisState


def _route_after_execute(state: AnalysisState) -> str:
    last = state["code_history"][-1]
    if last.success:
        return "interpret_results"
    if state["fix_attempts"] < _MAX_FIX_ATTEMPTS:
        return "fix_code"
    return "interpret_results"


def _route_after_interpret(state: AnalysisState) -> str:
    if state["current_step_index"] >= len(state["analysis_plan"]):
        return "generate_report"
    return "generate_code"


def build_graph():
    checkpointer = MemorySaver()
    graph = StateGraph(AnalysisState)

    graph.add_node("load_data", load_data)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("generate_code", generate_code)
    graph.add_node("execute_code", execute_code)
    graph.add_node("fix_code", fix_code)
    graph.add_node("interpret_results", interpret_results)
    graph.add_node("generate_report", generate_report)

    graph.add_edge(START, "load_data")
    graph.add_edge("load_data", "plan_analysis")
    graph.add_edge("plan_analysis", "generate_code")
    graph.add_edge("generate_code", "execute_code")
    graph.add_conditional_edges(
        "execute_code",
        _route_after_execute,
        {"interpret_results": "interpret_results", "fix_code": "fix_code"},
    )
    graph.add_edge("fix_code", "execute_code")
    graph.add_conditional_edges(
        "interpret_results",
        _route_after_interpret,
        {"generate_code": "generate_code", "generate_report": "generate_report"},
    )
    graph.add_edge("generate_report", END)

    return graph.compile(checkpointer=checkpointer)
