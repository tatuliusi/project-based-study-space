# Project 07 — Memory Engine

This service demonstrates a simple, practical memory system for personalizing AI responses.

In plain language: the app keeps three types of user memory — short text embeddings, a timeline of events, and a small preference profile — and it uses those memories to make replies more helpful and consistent.

## Key features

- Three memory types: semantic (vector search in Qdrant), episodic (events in Postgres), and preferences (structured profile).
- Per-turn flow: retrieve relevant memories, build a small context, call the LLM to respond, then extract and store new memories.
- Nightly consolidation: older episodic events are clustered and summarized into compact semantic memories.
- Duplicate protection: semantic inserts use an embedding-similarity guard to avoid near-duplicates.
- Privacy controls: endpoints to delete a memory or delete all user data.

## Tech stack

- `LangGraph` — orchestrates per-turn and consolidation graphs
- `Qdrant` — semantic memory (embeddings + nearest-neighbor search)
- `Postgres` — episodic timeline and preference records
- `FastAPI` — REST API surface
- `APScheduler` — schedules consolidation jobs
- `OpenAI` — embeddings and chat/extraction models
- `Pydantic v2` — typed schemas for extraction and profiles

## Quickstart (local)

1. Open the project folder and create a venv:

```bash
cd project-07-memory-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy environment template and set keys:

```bash
cp .env.example .env
# Set OPENAI_API_KEY, POSTGRES_DSN, QDRANT_HOST (see .env.example)
```

3. Start dependencies with Docker Compose:

```bash
docker compose up -d
```

4. Run the API server:

```bash
uvicorn src.api.main:app --reload
```

The HTTP API will be available at `http://localhost:8000`.

## Important environment variables

- `OPENAI_API_KEY`: API key for embeddings and chat/extraction.
- `POSTGRES_DSN`: Postgres connection string (used for episodes & profiles).
- `QDRANT_HOST`: Qdrant host URL (used for vector storage).
- `CONSOLIDATION_CRON`: Cron expression for nightly consolidation (optional).

See `.env.example` for defaults and more options.

## API (most-used endpoints)

- `POST /chat` — Send a user message. Body: `{"user_id": "alice", "message": "..."}`. Returns a reply plus which memories were used.
- `GET /users/{id}/memories` — Get semantic memories and preference profile for a user.
- `DELETE /users/{id}/memories/{mem_id}` — Delete one semantic memory.
- `DELETE /users/{id}` — Delete all data for a user (right-to-be-forgotten).
- `POST /consolidate/{id}` — Manually trigger consolidation for a user.

Example: send a chat message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "I prefer short answers. I work on a FastAPI project."}'
```

Example: trigger consolidation

```bash
curl -X POST http://localhost:8000/consolidate/alice
```

## How it works (short)

- Per-turn: the service loads semantic neighbors, recent episodic events, and the user's profile; it ranks and constructs a compact context; the LLM responds; an extraction step turns parts of the reply into structured memories that get written back.
- Consolidation: a background job groups older episodes, summarizes clusters with the LLM, writes compact summaries to Qdrant, and removes or marks the raw episodes.

## Where to look in code

- Runtime entry: [project-07-memory-engine/src/api/main.py](project-07-memory-engine/src/api/main.py)
- Graphs and nodes: [project-07-memory-engine/src/graph](project-07-memory-engine/src/graph)
- Memory models: [project-07-memory-engine/src/models.py](project-07-memory-engine/src/models.py)

For design rationale and diagrams see [project-07-memory-engine/ARCHITECTURE.md](project-07-memory-engine/ARCHITECTURE.md).

## Troubleshooting

- If Qdrant or Postgres fail to start, run `docker compose ps` and check logs with `docker compose logs qdrant` or `docker compose logs postgres`.
- If embeddings fail, confirm `OPENAI_API_KEY` is set and reachable.

## Tests & development

Run the small unit tests in the `tests/` directory with `pytest` after installing dev requirements.

---
If you'd like, I can also add a short example script that exercises the `/chat` and `/consolidate` endpoints. Want that added?
