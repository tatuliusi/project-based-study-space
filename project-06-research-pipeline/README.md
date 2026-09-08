# Project 6 — Scheduled Research-to-Report Pipeline

A production-ready async pipeline that accepts a research topic, fans out to multiple parallel research branches, fact-checks claims, and delivers a formatted Markdown or PDF report — on-demand or on a cron schedule.

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

## Quick start

1. Create and activate a virtual environment, install deps, and copy the example env:

```bash
cd project-06-research-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Populate .env with required keys (see Environment variables)
```

2. Start Redis (uses the included compose file):

```bash
docker compose up -d redis
```

3. Start the API server:

```bash
uvicorn src.api.main:app --reload
```

4. (Optional) Start the scheduler for cron-driven runs:

```bash
python -m src.scheduler.scheduler
```

## Environment variables

- `OPENAI_API_KEY` — OpenAI API key for synthesis and checks
- `TAVILY_API_KEY` — (optional) Tavily/search API key for web searches
- `REDIS_URL` — Redis connection string (e.g. `redis://localhost:6379/0`)
- `REPORT_STORAGE_PATH` — (optional) local path to persist generated artifacts
- `WEBHOOK_URL` — (optional) notify an external endpoint on job completion

## API examples

Submit a new report request:

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{"topic": "The future of renewable energy in Southeast Asia"}'
```

Poll job status:

```bash
curl http://localhost:8000/reports/<JOB_ID>/status
```

Download PDF after completion:

```bash
curl -o report.pdf http://localhost:8000/reports/<JOB_ID>/pdf
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

See `ARCHITECTURE.md` for the full design and [src/](src/) for implementation details.

## Development notes

- Core API: `src.api.main` and `src.api.*` handlers
- Graph & pipeline: `src.graph` (LangGraph orchestration)
- Scheduler entrypoint: `src.scheduler.scheduler`
- Rendering templates: `templates/` (HTML used by WeasyPrint)

If you'd like, I can also add a small example script to submit sample jobs automatically.
