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
| `project-06-research-pipeline/` | Scheduled Research-to-Report Pipeline | LangGraph Send API, APScheduler, Redis, WeasyPrint | Planned |
| `project-07-memory-engine/` | Semantic Memory & Personalization Engine | LangGraph, Qdrant, Postgres, APScheduler | Planned |
| `project-08-eval-framework/` | LLM Evaluation & Quality Gate System | LangGraph, LLM-as-judge, Postgres, GitHub Actions | Planned |
| `project-09-swe-agent/` | Autonomous SWE Agent | LangGraph, Docker SDK, GitHub API, Tree-sitter | Planned |
| `project-10-reasoning-swarm/` | Multi-Agent Reasoning Swarm | LangGraph subgraphs, SSE, Postgres | Planned |

## Shared conventions

- Python 3.11+
- LangGraph for all orchestration — no plain chains where a graph is appropriate
- Pydantic v2 for structured outputs
- Each project is self-contained with its own `requirements.txt` and `.env.example`
- Each project has `README.md` (usage) and `ARCHITECTURE.md` (graph design, data flow)
