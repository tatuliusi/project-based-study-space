from typing import Any

from langchain_community.callbacks import get_openai_callback
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src.logger import ResearchTrace
from src.nodes import evaluate_node, generate_node, plan_node, route_after_evaluate, search_node
from src.schemas import CoverageVerdict, ResearchReport


class ResearchState(TypedDict):
    query: str
    planned_queries: list[str]
    search_results: list[dict]
    iteration: int
    coverage_verdict: CoverageVerdict
    report: ResearchReport
    trace: ResearchTrace


def build_graph() -> Any:
    graph = StateGraph(ResearchState)

    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"generate": "generate", "plan": "plan"},
    )
    graph.add_edge("generate", END)

    return graph.compile()


def research(query: str, on_step=None) -> tuple[ResearchReport, ResearchTrace]:
    trace = ResearchTrace(query=query, on_step=on_step)
    app = build_graph()

    with get_openai_callback() as cb:
        result = app.invoke({
            "query": query,
            "planned_queries": [],
            "search_results": [],
            "iteration": 1,
            "coverage_verdict": None,
            "report": None,
            "trace": trace,
        })

    trace.total_tokens = cb.total_tokens
    trace.total_cost_usd = cb.total_cost

    return result["report"], trace
