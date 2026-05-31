# project-based-study-space

A collection of AI engineering portfolio projects built with LangGraph and the broader LLM ecosystem.

## Projects

| Directory | Project | Stack | Status |
|-----------|---------|-------|--------|
| `project-01-rag-qa-agent/` | RAG Q&A Agent | LangGraph, FAISS, Streamlit | In progress |
| `project-02-research-agent/` | Multi-source Research Agent | LangGraph, Tavily, Pydantic | Planned |
| `project-03-code-review-agent/` | Code Review Multi-Agent | LangGraph supervisor, GitHub API | Planned |
| `project-04-data-analyst-agent/` | Autonomous Data Analyst | LangGraph, code execution, pandas | Planned |
| `project-05-production-support/` | Production Support System | LangGraph, FastAPI, Postgres | Planned |

## Shared conventions

- Python 3.11+
- LangGraph for all orchestration — no plain chains where a graph is appropriate
- Pydantic v2 for structured outputs
- Each project is self-contained with its own `requirements.txt` and `.env.example`
- Each project has `README.md` (usage) and `ARCHITECTURE.md` (graph design, data flow)
