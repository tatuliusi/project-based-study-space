# Architecture — RAG Q&A Agent

## Why LangGraph instead of a plain chain

A plain LangChain RAG chain always retrieves and generates — it has no ability to check whether the retrieved documents are actually useful, and it cannot retry with a better query. LangGraph lets us model this as a stateful graph with conditional routing, which is how real production RAG systems work.

## Implementation entry point

The graph wiring and conditional routing are implemented in `src/graph.py`.

## State

```python
class RAGState(TypedDict):
    query: str           # The user's original or rewritten question
    documents: list      # Retrieved documents from the vector store
    generation: str      # The LLM's answer
    rewrite_count: int   # Guard against infinite rewrite loops
```

## Nodes

### `retrieve`
Embeds the current `query`, searches FAISS for the top-k most similar document chunks, stores them in `state["documents"]`.

### `grade_relevance`
Sends each retrieved document to an LLM grader with a binary prompt: "Is this document relevant to the query? Answer yes or no." Filters the list down to only relevant documents. If none remain, routes to `rewrite_query`. If at least one is relevant, routes to `generate`.

### `rewrite_query`
Asks the LLM to rewrite the original query to be more specific or precise, then loops back to `retrieve`. Capped at 2 rewrites to prevent infinite loops.

### `generate`
Sends the filtered relevant documents + query to the LLM. Produces an answer with explicit source citations (document name + page number where available).

## Graph

```
START
  │
  ▼
retrieve  ◄──────────────────────────────┐
  │                                      │
  ▼                                      │
grade_relevance                          │
  │                                      │
  ├─── [all irrelevant + rewrites < 2] ──► rewrite_query
  │
  ├─── [all irrelevant + rewrites >= 2] ──► generate (with disclaimer)
  │
  └─── [at least one relevant] ──────────► generate
                                               │
                                               ▼
                                             END
```

## Vector store design

- **Chunking:** 1000 characters, 200 overlap — standard for mixed document types
- **Embedding model:** `text-embedding-3-small` — cheap, fast, good enough for retrieval
- **Store:** FAISS in-memory, persisted to disk after ingestion
- **Top-k:** 4 documents per query (tunable)

## Why relevance grading matters

Without grading, a RAG system will confidently answer from irrelevant context. Grading catches the "I have chunks but none of them address the question" case and either retries or tells the user the document doesn't contain the answer. This is the difference between a demo and something that works reliably.
