from typing import TypedDict

from langchain_community.vectorstores import FAISS
from langgraph.graph import END, START, StateGraph

from src.nodes import (
    generate_node,
    grade_relevance_node,
    retrieve_node,
    rewrite_query_node,
    route_after_grading,
)


class RAGState(TypedDict):
    query: str
    documents: list
    generation: str
    rewrite_count: int


def build_graph(store: FAISS) -> StateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", lambda s: retrieve_node(s, store))
    graph.add_node("grade_relevance", grade_relevance_node)
    graph.add_node("generate", generate_node)
    graph.add_node("rewrite_query", rewrite_query_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "grade_relevance")
    graph.add_conditional_edges(
        "grade_relevance",
        route_after_grading,
        {"generate": "generate", "rewrite": "rewrite_query"},
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("generate", END)

    return graph.compile()


def ask(query: str, store: FAISS) -> str:
    app = build_graph(store)
    result = app.invoke({"query": query, "documents": [], "generation": "", "rewrite_count": 0})
    return result["generation"]
