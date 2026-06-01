from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.nodes import (
    fetch_pr_diff_node,
    generate_review,
    logic_agent,
    parse_diff_node,
    security_agent,
    style_agent,
)
from src.schemas import CodeReview
from src.state import ReviewState


def _dispatch(state: ReviewState) -> list[Send]:
    snapshot = dict(state)
    return [
        Send("security_agent", snapshot),
        Send("logic_agent", snapshot),
        Send("style_agent", snapshot),
    ]


def build_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("fetch_pr_diff", fetch_pr_diff_node)
    graph.add_node("parse_diff", parse_diff_node)
    graph.add_node("security_agent", security_agent)
    graph.add_node("logic_agent", logic_agent)
    graph.add_node("style_agent", style_agent)
    graph.add_node("generate_review", generate_review)

    graph.add_edge(START, "fetch_pr_diff")
    graph.add_edge("fetch_pr_diff", "parse_diff")
    graph.add_conditional_edges("parse_diff", _dispatch, ["security_agent", "logic_agent", "style_agent"])
    graph.add_edge("security_agent", "generate_review")
    graph.add_edge("logic_agent", "generate_review")
    graph.add_edge("style_agent", "generate_review")
    graph.add_edge("generate_review", END)

    return graph.compile()


def review_pr(pr_url: str) -> CodeReview:
    app = build_graph()
    result = app.invoke({
        "pr_url": pr_url,
        "diff": "",
        "file_summaries": [],
        "security_findings": [],
        "logic_findings": [],
        "style_findings": [],
        "final_review": None,
    })
    return result["final_review"]
