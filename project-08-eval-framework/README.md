# Project 8 — LLM Evaluation & Quality Gate System

An automated evaluation framework for LLM applications: define test suites, run them against any LLM app, score results with LLM-as-judge and deterministic metrics, track regressions over time, and block deploys when quality drops.

## What this demonstrates

- LLM-as-judge: a separate evaluator model scores outputs against a rubric
- RAGAS-style metrics implemented from scratch: faithfulness, answer relevance, context precision
- Evaluation dataset management: create, version, and run datasets
- Regression detection: compare eval runs across model/prompt versions
- CI/CD integration: GitHub Actions webhook triggers eval runs; pass/fail gate returns exit code

## Stack

- **LangGraph** — evaluation pipeline graph (load → run → judge → score → report)
- **FastAPI** — REST API for dataset management and run triggers
- **Postgres** — eval run history, dataset versions, per-sample scores
- **OpenAI** — app-under-test + evaluator judge model (separate instances)
- **Pydantic v2** — dataset schemas, score schemas, report schemas
- **GitHub Actions** — CI webhook consumer (optional integration)

## Setup

```bash
cd project-08-eval-framework
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY, DATABASE_URL, APP_UNDER_TEST_URL to .env

docker compose up -d db
python src/db/migrate.py

uvicorn src.api.main:app --reload
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/datasets` | Create an eval dataset |
| POST | `/datasets/{id}/samples` | Add input/expected pairs |
| POST | `/runs` | Trigger an eval run (dataset + app config) |
| GET | `/runs/{id}` | Get run results and per-sample scores |
| GET | `/runs/{id}/report` | Get summary report with pass/fail gate |
| GET | `/runs/compare?a={id}&b={id}` | Regression diff between two runs |
| POST | `/webhook/github` | GitHub Actions integration endpoint |

## Graph overview

```
START
  │
  ▼
load_dataset           (fetch all samples for this run)
  │
  ├─ Send(run_sample, sample_1)
  ├─ Send(run_sample, sample_2)   ← parallel: one branch per sample
  └─ ...
       │ (fan-in)
       ▼
aggregate_scores       (compute mean/p50/p95 per metric across all samples)
  │
  ▼
detect_regression      (compare against baseline run if provided)
  │
  ▼
generate_report        (structured report with pass/fail per metric)
  │
  ▼
store_results          (persist to Postgres, update run status)
  │
  ▼
END
```

**Per-sample branch:**
```
run_sample → call_app → judge_output → score_metrics → return scores
```

See `ARCHITECTURE.md` for the full design.
