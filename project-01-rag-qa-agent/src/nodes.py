from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.retriever import retrieve

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

_MAX_REWRITE_ATTEMPTS = 2
_MAX_DOC_PREVIEW_CHARS = 500


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
    trace = state["trace"]
    query = state["query"]
    trace.add("retrieve", f"searching for: '{query}'")
    docs = retrieve(query, store)
    trace.add("retrieve", f"found {len(docs)} chunk(s)")
    return {"documents": docs}


def grade_relevance_node(state: dict) -> dict:
    trace = state["trace"]
    query = state["query"]
    relevant = []
    for i, doc in enumerate(state["documents"]):
        result = _grader.invoke(GRADE_PROMPT.format(query=query, doc=doc.page_content[:_MAX_DOC_PREVIEW_CHARS]))
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        verdict = "relevant" if result.relevant else "irrelevant"
        trace.add("grade", f"chunk {i+1} [{source} p.{page}] → {verdict}")
        if result.relevant:
            relevant.append(doc)
    trace.add("grade", f"{len(relevant)}/{len(state['documents'])} chunks passed")
    return {"documents": relevant}


def generate_node(state: dict) -> dict:
    trace = state["trace"]
    docs: list[Document] = state["documents"]
    query = state["query"]

    if not docs:
        trace.add("generate", "no relevant docs — returning fallback response")
        return {"generation": "I could not find relevant information in the uploaded documents to answer this question."}

    context = "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}, page {doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in docs
    )
    trace.add("generate", f"generating answer from {len(docs)} chunk(s)")
    generation = _llm.invoke(GENERATE_PROMPT.format(context=context, query=query)).content
    trace.add("generate", "answer ready")
    return {"generation": generation}


def rewrite_query_node(state: dict) -> dict:
    trace = state["trace"]
    original = state["query"]
    rewritten = _llm.invoke(REWRITE_PROMPT.format(query=original)).content.strip()
    count = state.get("rewrite_count", 0) + 1
    trace.add("rewrite", f"attempt {count}: '{original}' → '{rewritten}'")
    return {"query": rewritten, "rewrite_count": count}


def route_after_grading(state: dict) -> str:
    if state["documents"]:
        return "generate"
    if state.get("rewrite_count", 0) >= _MAX_REWRITE_ATTEMPTS:
        return "generate"
    return "rewrite"
