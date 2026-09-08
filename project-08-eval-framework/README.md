# Project 08 - LLM Evaluation & Quality Gate System

Evaluation infrastructure for LLM applications: run datasets through an app under test, score outputs with deterministic metrics and an LLM-as-judge, detect regressions against a baseline, and block CI deploys that fail the quality gate.

## Stack

- **LangGraph** - eval pipeline with Send API fan-out (one node per sample, parallel)
- **LLM-as-judge** - GPT-4o scores outputs on correctness, faithfulness, answer relevance, context precision, tone
- **FastAPI** - REST API for datasets, runs, and GitHub webhook integration
- **Postgres** - stores datasets, runs, and reports
- **GitHub Actions** - CI gate via POST to `/webhook/github`

## Quick start

```bash
cd project-08-eval-framework
cp .env.example .env
# fill in OPENAI_API_KEY

docker compose up -d

pip install -r requirements.txt

python -m src
```

API is at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Usage

### 1. Create a dataset

```bash
curl -X POST http://localhost:8000/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rag-qa-v1",
    "metric_set": ["exact_match", "faithfulness", "answer_relevance"],
    "samples": [
      {
        "input": "What is the capital of France?",
        "expected_output": "Paris",
        "context": ["France is a country in Western Europe. Its capital is Paris."]
      }
    ]
  }'
```

### 2. Start an eval run

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "<id from above>",
    "app_config": {"app_id": "my-rag-app", "model": "gpt-4o-mini", "prompt_version": "v1"}
  }'
```

### 3. Fetch the report

```bash
curl http://localhost:8000/runs/<run_id>
```

### 4. CI gate

The GitHub Actions workflow in `.github/workflows/eval.yml` posts to `/webhook/github` on every push. Returns HTTP 200 (pass) or HTTP 422 (fail with regression details). Set repo variables: `EVAL_SERVICE_URL`, `EVAL_DATASET_ID`, `APP_MODEL`.

## Graph overview

```
START
  |
  +-- Send(evaluate_sample, s1)
  +-- Send(evaluate_sample, s2)   <- parallel per sample
  +-- Send(evaluate_sample, sN)
       | (fan-in via operator.add reducer)
       v
  aggregate_results    <- mean/min/max/std per metric
       |
       v
  detect_regressions   <- compare to baseline, check absolute floor
       |
       v
  build_report         <- final EvalReport with pass/fail
       |
       v
  END
```

## Running tests

```bash
pytest tests/ -v
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required |
| `JUDGE_MODEL` | `gpt-4o` | Model used to score outputs |
| `APP_MODEL` | `gpt-4o-mini` | Model used as the app under test |
| `POSTGRES_DSN` | local | Asyncpg connection string |
| `REGRESSION_THRESHOLD` | `0.05` | Drop in mean score that triggers a regression |
| `ABSOLUTE_FLOOR_CORRECTNESS` | `0.7` | Correctness below this always fails |
| `SAMPLE_REPEATS` | `3` | Times each sample is run (mean is taken) |

See `ARCHITECTURE.md` for the full design rationale and interview prep notes.
