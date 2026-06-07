# Project 7 — Semantic Memory & Personalization Engine

A personal AI assistant that builds and queries a three-tier memory system — semantic (vector), episodic (structured events), and preference (explicit user model) — and uses those memories to personalize every response.

## What this demonstrates

- Three-tier memory architecture: semantic (Qdrant), episodic (Postgres), preference (structured profile)
- Memory consolidation: background agent that merges, deduplicates, and summarizes old memories
- Retrieval-augmented generation with user-specific context (not just documents)
- LangGraph graph with a memory-read → respond → memory-write lifecycle per turn
- Explicit user modeling: preference extraction from conversation history

## Stack

- **LangGraph** — per-turn graph + background consolidation graph
- **Qdrant** — semantic memory (dense vector search over past interactions)
- **Postgres** — episodic memory (timestamped event log with structured metadata)
- **FastAPI** — REST API
- **OpenAI** — chat agent + embedding model
- **Pydantic v2** — memory schemas, user profile model

## Setup

```bash
cd project-07-memory-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY, QDRANT_URL, DATABASE_URL to .env

docker compose up -d qdrant db

python src/db/migrate.py

uvicorn src.api.main:app --reload
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/users` | Create a user profile |
| POST | `/users/{id}/chat` | Send a message; returns personalized response |
| GET | `/users/{id}/memories` | List retrieved memories for last turn |
| GET | `/users/{id}/profile` | Get structured preference profile |
| DELETE | `/users/{id}/memories/{mem_id}` | Forget a specific memory |
| POST | `/users/{id}/consolidate` | Trigger manual memory consolidation |

## Graph overview

**Per-turn graph:**
```
START
  │
  ▼
retrieve_memories      (query all three tiers for relevant context)
  │
  ▼
build_context          (rank and assemble top-K memories into prompt context)
  │
  ▼
respond                (LLM generates personalized response)
  │
  ▼
extract_memories       (identify new facts, preferences, events from this turn)
  │
  ▼
write_memories         (upsert semantic + episodic; update preference profile)
  │
  ▼
END
```

**Background consolidation graph (runs nightly):**
```
START → load_old_episodes → cluster_similar → merge_clusters → write_summaries → prune_originals → END
```

See `ARCHITECTURE.md` for the full design.
