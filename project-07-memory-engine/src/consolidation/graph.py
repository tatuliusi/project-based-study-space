from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.consolidation.nodes import (
    cluster_similar,
    load_old_episodes,
    merge_clusters,
    prune_originals,
    write_summaries,
)
from src.consolidation.state import ConsolidationState


def build_consolidation_graph() -> StateGraph:
    g = StateGraph(ConsolidationState)

    g.add_node("load_old_episodes", load_old_episodes)
    g.add_node("cluster_similar", cluster_similar)
    g.add_node("merge_clusters", merge_clusters)
    g.add_node("write_summaries", write_summaries)
    g.add_node("prune_originals", prune_originals)

    g.add_edge(START, "load_old_episodes")
    g.add_edge("load_old_episodes", "cluster_similar")
    g.add_edge("cluster_similar", "merge_clusters")
    g.add_edge("merge_clusters", "write_summaries")
    g.add_edge("write_summaries", "prune_originals")
    g.add_edge("prune_originals", END)

    return g.compile()


consolidation_graph = build_consolidation_graph()
