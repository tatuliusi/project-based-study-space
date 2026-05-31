# Project 1 — RAG Q&A Agent

A document question-answering system built with LangGraph. Upload PDFs or text files, ask questions, get answers with source citations.

## What this demonstrates

- Retrieval-Augmented Generation (RAG) pipeline
- LangGraph state graph with conditional routing
- Relevance grading — the agent checks if retrieved docs actually answer the question before generating
- Query rewriting — if retrieved docs are irrelevant, the agent rewrites the query and retries
- Source citation in every answer

## Stack

- **LangGraph** — orchestration and state management
- **FAISS** — local vector store for document embeddings
- **OpenAI** — embeddings (`text-embedding-3-small`) and generation (`gpt-4o-mini`)
- **LangChain** — document loaders, text splitters
- **Streamlit** — web UI

## Setup

```bash
cd project-01-rag-qa-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Run

```bash
streamlit run src/app.py
```

## Project structure

```
project-01-rag-qa-agent/
├── src/
│   ├── graph.py          # LangGraph state graph definition
│   ├── nodes.py          # Node functions (retrieve, grade, generate, rewrite)
│   ├── retriever.py      # Vector store setup and document ingestion
│   └── app.py            # Streamlit UI
├── docs/                 # Sample documents for testing
├── requirements.txt
├── .env.example
├── README.md
└── ARCHITECTURE.md
```

## Graph overview

```
START → retrieve → grade_relevance → [relevant] → generate → END
                                   → [not relevant] → rewrite_query → retrieve
```

See `ARCHITECTURE.md` for the full graph design.
