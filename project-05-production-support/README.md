# Project 5 — Production Customer Support System

A multi-agent customer support system with triage routing, specialist agents, persistent conversation memory, human escalation, streaming responses, and a FastAPI backend.

## What this demonstrates

- Production LangGraph: persistent checkpointing with Postgres
- Streaming responses over Server-Sent Events
- Human-in-the-loop escalation flow
- Multi-agent routing (triage → specialist)
- Cross-session memory per user
- FastAPI deployment with async LangGraph execution

## Stack

- **LangGraph** — orchestration with Postgres checkpointer
- **FastAPI** — async HTTP backend with SSE streaming
- **Postgres** — state persistence across sessions
- **OpenAI** — triage and specialist agents
- **Pydantic v2** — request/response schemas
- **Streamlit** — demo frontend

## Setup

```bash
cd project-05-production-support
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY and DATABASE_URL to .env

# Start Postgres (Docker)
docker compose up -d db

# Run migrations
python src/db/migrate.py

# Start API
uvicorn src.api.main:app --reload
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/conversations` | Start a new support conversation |
| POST | `/conversations/{id}/messages` | Send a message, stream the response |
| GET | `/conversations/{id}` | Get full conversation history |
| POST | `/conversations/{id}/escalate` | Human escalation trigger |

## Graph overview

```
START → triage → [billing] → billing_agent → respond → END
               → [technical] → technical_agent → respond → END
               → [complaint] → complaint_agent → respond → END
               → [escalate] → human_handoff → END
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.
