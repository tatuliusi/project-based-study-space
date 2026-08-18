from typing import TypedDict

from langchain_community.callbacks import get_openai_callback
from langchain_community.vectorstores import FAISS
from langgraph.graph import END, START, StateGraph

from src.logger import QueryTrace
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
    trace: QueryTrace


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


def ask(query: str, store: FAISS | None) -> tuple[str, QueryTrace]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("Query must be a non-empty string.")
    if store is None:
        raise ValueError("A vector store is required. Please index at least one document first.")

    trace = QueryTrace(query=cleaned_query)
    app = build_graph(store)

    with get_openai_callback() as cb:
        result = app.invoke({
            "query": cleaned_query,
            "documents": [],
            "generation": "",
            "rewrite_count": 0,
            "trace": trace,
        })

    trace.total_tokens = cb.total_tokens
    trace.total_cost_usd = cb.total_cost

    return result["generation"], trace
