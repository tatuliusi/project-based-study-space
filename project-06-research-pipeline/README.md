# Project 6 — Scheduled Research-to-Report Pipeline

A production-grade async pipeline that accepts a research topic, fans out to multiple parallel research branches, fact-checks claims, and delivers a formatted Markdown or PDF report — either on-demand or on a cron schedule.

## What this demonstrates

- Parallel LangGraph branches with `Send` API (fan-out / fan-in)
- Scheduled agentic execution (APScheduler + FastAPI lifespan)
- Source credibility scoring and fact-checking loop
- Structured final report rendering (Markdown → PDF via WeasyPrint)
- Async task queue pattern: submit job, poll status, retrieve artifact

## Stack

- **LangGraph** — orchestration with `Send` for parallel branches
- **Tavily** — web search per sub-topic
- **APScheduler** — cron-triggered pipeline runs
- **FastAPI** — async REST API + job queue
- **WeasyPrint** — HTML/CSS → PDF rendering
- **Redis** — job state and result storage
- **Pydantic v2** — schemas for subtopics, findings, final report
- **OpenAI** — synthesis and fact-checking agents

## Setup

```bash
cd project-06-research-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY, TAVILY_API_KEY, REDIS_URL to .env

# Start Redis
docker compose up -d redis

# Start API
uvicorn src.api.main:app --reload
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reports` | Submit a research topic; returns job ID |
| GET | `/reports/{id}/status` | Poll job status (queued / running / done / failed) |
| GET | `/reports/{id}` | Retrieve structured report JSON |
| GET | `/reports/{id}/pdf` | Download rendered PDF |
| POST | `/schedules` | Create a recurring report schedule (cron expression) |
| GET | `/schedules` | List active schedules |
| DELETE | `/schedules/{id}` | Delete a schedule |

## Graph overview

```
START
  │
  ▼
decompose_topic          (break topic into 4–6 sub-topics)
  │
  ├─ Send(research, sub_topic_1)
  ├─ Send(research, sub_topic_2)   ← parallel branches via Send API
  ├─ Send(research, sub_topic_3)
  └─ ...
       │
       ▼ (fan-in: all branches complete)
  fact_check              (cross-check claims, score source credibility)
       │
       ▼
  synthesize              (merge findings into coherent narrative)
       │
       ▼
  format_report           (structure into sections with citations)
       │
       ▼
  render_pdf              (HTML template → PDF via WeasyPrint)
       │
       ▼
  store_artifact          (write to Redis, notify webhook if configured)
       │
       ▼
END
```

See `ARCHITECTURE.md` for the full design.
