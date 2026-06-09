from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.graph.nodes import (
    decompose_topic,
    fact_check,
    format_report,
    render_pdf,
    research_branch,
    store_artifact,
    synthesize,
)
from src.graph.state import BranchState, PipelineState


def _fan_out(state: PipelineState) -> list[Send]:
    return [Send("research_branch", {"sub_topic": t}) for t in state["sub_topics"]]


def build_pipeline() -> StateGraph:
    builder = StateGraph(PipelineState)

    builder.add_node("decompose_topic", decompose_topic)
    builder.add_node("research_branch", research_branch)
    builder.add_node("fact_check", fact_check)
    builder.add_node("synthesize", synthesize)
    builder.add_node("format_report", format_report)
    builder.add_node("render_pdf", render_pdf)
    builder.add_node("store_artifact", store_artifact)

    builder.add_edge(START, "decompose_topic")
    builder.add_conditional_edges("decompose_topic", _fan_out, ["research_branch"])
    builder.add_edge("research_branch", "fact_check")
    builder.add_edge("fact_check", "synthesize")
    builder.add_edge("synthesize", "format_report")
    builder.add_edge("format_report", "render_pdf")
    builder.add_edge("render_pdf", "store_artifact")
    builder.add_edge("store_artifact", END)

    return builder.compile()


pipeline = build_pipeline()
