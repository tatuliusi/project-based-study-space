# Project 7 — Semantic Memory & Personalization Engine

A personal AI assistant that builds and queries a three-tier memory system — semantic (vector), episodic (structured events), and preference (explicit user model) — and uses those memories to personalize every response.

## What this demonstrates

- Three-tier memory architecture: semantic (Qdrant), episodic (Postgres), preference (structured profile)
- Memory consolidation: background LangGraph that clusters, merges, and prunes old episodic memories
- Retrieval-augmented generation with user-specific context (not just documents)
- Per-turn LangGraph lifecycle: retrieve → build context → respond → extract → write
- Explicit user modeling: preference extraction via structured LLM output (Pydantic)
- Cosine dedup guard: prevents inserting near-duplicate semantic memories (threshold 0.95)
- Right-to-be-forgotten endpoint: hard-deletes all user data from Qdrant and Postgres

## Stack

- **LangGraph** — per-turn graph + nightly background consolidation graph
- **Qdrant** — semantic memory (dense vector search, `text-embedding-3-small`, 1536 dims)
- **Postgres** — episodic memory (timestamped event log) + preference profiles
- **FastAPI** — REST API with lifespan startup (schema init + scheduler start)
- **APScheduler** — nightly consolidation cron (configurable via `CONSOLIDATION_CRON`)
- **OpenAI** — `gpt-4o-mini` for chat + extraction, `text-embedding-3-small` for embeddings
- **Pydantic v2** — memory schemas, extraction schema, preference profile

## Setup

```bash
cd project-07-memory-engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in OPENAI_API_KEY; adjust POSTGRES_DSN and QDRANT_HOST if needed

docker compose up -d          # starts Qdrant + Postgres

uvicorn src.api.main:app --reload
# Schema is auto-created on first startup via SQLAlchemy
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message; returns personalized reply + memories used |
| GET | `/users/{id}/memories` | List all semantic memories and preference profile |
| DELETE | `/users/{id}/memories/{mem_id}` | Forget a specific semantic memory |
| DELETE | `/users/{id}` | Right-to-be-forgotten: delete all user data |
| POST | `/consolidate/{id}` | Trigger manual nightly consolidation for a user |

### Chat example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "I prefer short answers. I am working on a FastAPI project."}'
```

## Graph overview

**Per-turn graph:**
```
START
  │
  ▼
retrieve_memories      (parallel: Qdrant similarity + Postgres episodes + profile load)
  │
  ▼
build_context          (rank by similarity × recency-decay × importance, inject top-K)
  │
  ▼
respond                (gpt-4o-mini with memory context in system prompt)
  │
  ▼
extract_memories       (structured LLM call → ExtractedMemories Pydantic schema)
  │
  ▼
write_memories         (upsert semantic with dedup; insert episodes; patch profile)
  │
  ▼
END
```

**Background consolidation graph (nightly, all users):**
```
START
  │
  ▼
load_old_episodes      (episodes older than 30 days)
  │
  ▼
cluster_similar        (k-means, k chosen by silhouette score)
  │
  ▼
merge_clusters         (LLM summarises each cluster → single semantic memory)
  │
  ▼
write_summaries        (upsert merged memories into Qdrant, importance=0.8)
  │
  ▼
prune_originals        (delete merged raw episodes from Postgres)
  │
  ▼
END
```

See `ARCHITECTURE.md` for full design rationale and interview Q&A.
