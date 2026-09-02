from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    analyze_failures,
    analyze_issue,
    create_plan,
    explore_repo,
    human_approval,
    implement,
    open_pr,
    patch_node,
    run_tests_node,
    should_iterate,
)
from .state import SWEState


def build_graph():
    builder = StateGraph(SWEState)

    builder.add_node("analyze_issue", analyze_issue)
    builder.add_node("explore_repo", explore_repo)
    builder.add_node("create_plan", create_plan)
    builder.add_node("implement", implement)
    builder.add_node("run_tests", run_tests_node)
    builder.add_node("analyze_failures", analyze_failures)
    builder.add_node("patch", patch_node)
    builder.add_node("human_approval", human_approval)
    builder.add_node("open_pr", open_pr)

    builder.add_edge(START, "analyze_issue")
    builder.add_edge("analyze_issue", "explore_repo")
    builder.add_edge("explore_repo", "create_plan")
    builder.add_edge("create_plan", "implement")
    builder.add_edge("implement", "run_tests")

    builder.add_conditional_edges(
        "run_tests",
        should_iterate,
        {"iterate": "analyze_failures", "approve": "human_approval"},
    )

    builder.add_edge("analyze_failures", "patch")
    builder.add_edge("patch", "run_tests")

    builder.add_edge("human_approval", "open_pr")
    builder.add_edge("open_pr", END)

    return builder.compile()


swe_graph = build_graph()
