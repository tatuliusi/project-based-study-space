# Architecture — Scheduled Research-to-Report Pipeline

## Why this project exists in the progression

Projects 1–5 run on-demand in response to a single user message. This project introduces two new production concerns:

1. **Scheduled, unattended execution** — cron triggers, no human in the loop to start it
2. **Parallel agent branches** — the `Send` API fans out research to N sub-agents simultaneously, then fans back in for synthesis

## Implementation entry point

The scheduled pipeline graph and fan-out routing are organized under `src/graph/`.

## State

```python
class PipelineState(TypedDict):
    job_id: str
    topic: str
    sub_topics: list[str]
    findings: Annotated[list[Finding], operator.add]   # fan-in reducer
    fact_check_results: list[FactCheckResult]
    report: Report | None
    artifact_url: str | None
    status: Literal["running", "done", "failed"]
    error: str | None

class Finding(BaseModel):
    sub_topic: str
    summary: str
    sources: list[Source]
    confidence: float  # 0.0–1.0 based on source credibility

class Source(BaseModel):
    url: str
    title: str
    snippet: str
    domain_credibility: float   # scored by fact-check agent
```

## Parallel fan-out with the Send API

```python
def decompose_topic(state: PipelineState) -> list[Send]:
    sub_topics = decompose_llm_call(state["topic"])
    return [Send("research_branch", {"sub_topic": t}) for t in sub_topics]
```

Each `Send` launches an independent `research_branch` node in parallel. LangGraph collects all `Finding` results via the `operator.add` reducer on `findings` before proceeding to `fact_check`.

This is the key LangGraph pattern: fan-out with `Send`, fan-in with a reducer.

## Nodes

### decompose_topic
Calls the LLM to break the topic into 4–6 focused sub-topics. Returns a list of `Send` objects — one per branch.

### research_branch (runs N times in parallel)
- Calls Tavily with the sub-topic query
- Extracts key claims from each result
- Returns a `Finding` with sources and raw claims

### fact_check
- For each unique claim across all findings, cross-references with a second Tavily query
- Scores source credibility (domain, date, citation count heuristics)
- Filters out low-confidence claims (< 0.4)

### synthesize
- Merges all verified findings into a coherent narrative
- Resolves contradictions by preferring higher-credibility sources
- Produces section outlines

### format_report
- Structures the narrative into a `Report` with sections, an executive summary, and a bibliography
- Report schema is Pydantic-validated, so downstream consumers get typed data

### render_pdf
- Renders a Jinja2 HTML template with the report data
- Converts HTML + CSS to PDF using WeasyPrint
- Uploads artifact to Redis with a TTL (default: 24 hours)

### store_artifact
- Writes final `Report` JSON and PDF URL to Redis under the `job_id`
- If a webhook URL was registered with the job, sends a POST notification

## Scheduling

```python
scheduler = AsyncIOScheduler()
scheduler.add_job(run_pipeline, "cron", hour=7, args=[topic, config])
```

APScheduler runs inside the FastAPI lifespan event. Schedules are persisted to a SQLite table so they survive restarts. Each scheduled run creates a new job record the same way an on-demand POST `/reports` does.

## Job lifecycle

```
POST /reports
    │
    ▼
create job record in Redis (status=queued)
    │
    ▼
enqueue background task (FastAPI BackgroundTasks or asyncio.create_task)
    │
    ▼
graph.ainvoke(state)  ← runs the full pipeline
    │
    ▼
update Redis (status=done, artifact_url=...)
    │
    ▼
GET /reports/{id}/pdf  ← client downloads artifact
```

## What an interviewer will ask about this

1. "How do you run agent branches in parallel in LangGraph?" — `Send` API in the router node; reducer aggregates results.
2. "What happens if one branch fails?" — Branch error is caught and written to `findings` with `confidence=0.0`; synthesize skips it; job still completes.
3. "How do you prevent the same report from running twice on a schedule?" — Redis SETNX on `schedule_id:running` acts as a distributed lock; APScheduler `misfire_grace_time` handles clock drift.
4. "How does the PDF rendering work?" — Jinja2 template → HTML string → WeasyPrint → bytes → stored in Redis as binary blob.
