from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.retriever import retrieve

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class GradeResult(BaseModel):
    relevant: bool


_grader = _llm.with_structured_output(GradeResult)

GRADE_PROMPT = """You are grading whether a document is relevant to a user query.
Query: {query}
Document: {doc}
Is this document relevant? Answer with relevant=true or relevant=false."""

GENERATE_PROMPT = """Answer the question using only the provided context.
At the end, list the sources you used (document name and page if available).
If the context does not contain the answer, say so explicitly — do not guess.

Context:
{context}

Question: {query}"""

REWRITE_PROMPT = """The retrieved documents were not relevant to this question.
Rewrite the question to be more specific and targeted for a document search.
Return only the rewritten question, nothing else.

Original question: {query}"""


def retrieve_node(state: dict, store) -> dict:
    docs = retrieve(state["query"], store)
    return {"documents": docs}


def grade_relevance_node(state: dict) -> dict:
    query = state["query"]
    relevant = []
    for doc in state["documents"]:
        result = _grader.invoke(GRADE_PROMPT.format(query=query, doc=doc.page_content[:500]))
        if result.relevant:
            relevant.append(doc)
    return {"documents": relevant}


def generate_node(state: dict) -> dict:
    docs: list[Document] = state["documents"]
    query = state["query"]

    if not docs:
        generation = "I could not find relevant information in the uploaded documents to answer this question."
        return {"generation": generation}

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}, page {doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in docs
    )
    generation = _llm.invoke(GENERATE_PROMPT.format(context=context, query=query)).content
    return {"generation": generation}


def rewrite_query_node(state: dict) -> dict:
    rewritten = _llm.invoke(REWRITE_PROMPT.format(query=state["query"])).content.strip()
    return {"query": rewritten, "rewrite_count": state.get("rewrite_count", 0) + 1}


def route_after_grading(state: dict) -> str:
    if state["documents"]:
        return "generate"
    if state.get("rewrite_count", 0) >= 2:
        return "generate"
    return "rewrite"
