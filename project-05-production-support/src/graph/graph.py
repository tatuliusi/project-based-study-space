from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from src.graph.nodes import (
    billing_node,
    complaint_node,
    human_handoff_node,
    load_user_context_node,
    summarize_session_node,
    technical_node,
    triage_node,
)
from src.graph.state import SupportState


def _route_after_triage(state: SupportState) -> str:
    if state["escalated"]:
        return "human_handoff"
    cat = state.get("category") or "unknown"
    mapping = {
        "billing": "billing",
        "technical": "technical",
        "complaint": "complaint",
        "unknown": "technical",
    }
    return mapping.get(cat, "technical")


def _route_after_complaint(state: SupportState) -> str:
    return "human_handoff" if state.get("escalated") else "summarize"


def build_graph(checkpointer: BaseCheckpointSaver):
    g = StateGraph(SupportState)

    g.add_node("load_context", load_user_context_node)
    g.add_node("triage", triage_node)
    g.add_node("billing", billing_node)
    g.add_node("technical", technical_node)
    g.add_node("complaint", complaint_node)
    g.add_node("human_handoff", human_handoff_node)
    g.add_node("summarize", summarize_session_node)

    g.set_entry_point("load_context")
    g.add_edge("load_context", "triage")

    g.add_conditional_edges(
        "triage",
        _route_after_triage,
        {
            "billing": "billing",
            "technical": "technical",
            "complaint": "complaint",
            "human_handoff": "human_handoff",
        },
    )

    g.add_edge("billing", "summarize")
    g.add_edge("technical", "summarize")
    g.add_conditional_edges(
        "complaint",
        _route_after_complaint,
        {"human_handoff": "human_handoff", "summarize": "summarize"},
    )
    g.add_edge("human_handoff", "summarize")
    g.add_edge("summarize", END)

    return g.compile(checkpointer=checkpointer)
