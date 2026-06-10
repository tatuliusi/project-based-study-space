from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    build_context,
    extract_memories,
    respond,
    retrieve_memories,
    write_memories,
)
from src.graph.state import TurnState


def build_turn_graph() -> StateGraph:
    g = StateGraph(TurnState)

    g.add_node("retrieve_memories", retrieve_memories)
    g.add_node("build_context", build_context)
    g.add_node("respond", respond)
    g.add_node("extract_memories", extract_memories)
    g.add_node("write_memories", write_memories)

    g.add_edge(START, "retrieve_memories")
    g.add_edge("retrieve_memories", "build_context")
    g.add_edge("build_context", "respond")
    g.add_edge("respond", "extract_memories")
    g.add_edge("extract_memories", "write_memories")
    g.add_edge("write_memories", END)

    return g.compile()


turn_graph = build_turn_graph()
