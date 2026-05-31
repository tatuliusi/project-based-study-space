# Architecture — Multi-source Research Agent

## Core pattern: ReAct loop with structured output

This agent uses a Reason → Act → Observe loop implemented as a LangGraph graph. The key difference from Project 1 is that the agent has **agency over its own search strategy** — it decides what to search, evaluates what it found, and decides whether to search more or stop.

## State

```python
class ResearchState(TypedDict):
    topic: str
    search_queries: list[str]        # Planned queries for this iteration
    web_results: list[SearchResult]  # Accumulated from all iterations
    paper_results: list[PaperResult] # Accumulated arxiv results
    iteration: int                   # Loop guard
    report: ResearchReport | None    # Final structured output
```

## Nodes

### `plan_searches`
LLM node. Given the topic and any results gathered so far, produces a list of specific search queries. On iteration 1, plans from scratch. On subsequent iterations, plans to fill gaps it identified in `evaluate_coverage`.

### `web_search`
Tool node. Calls Tavily API with each planned query in parallel. Returns structured results (title, URL, snippet, date).

### `arxiv_search`
Tool node. Calls arxiv API, filters to last 2 years, extracts title, abstract, authors, link.

### `evaluate_coverage`
LLM node. Reviews all accumulated results against the original topic. Produces a structured verdict: `{sufficient: bool, gaps: list[str], confidence: float}`. If not sufficient and iteration < 3, routes back to `plan_searches`.

### `generate_report`
LLM node with structured output. Produces a `ResearchReport` Pydantic model:

```python
class ResearchReport(BaseModel):
    title: str
    summary: str
    key_findings: list[Finding]
    academic_sources: list[Citation]
    web_sources: list[Citation]
    limitations: str
```

## Graph

```
START
  │
  ▼
plan_searches
  │
  ▼
web_search ──┐
             ├── (parallel) ──► evaluate_coverage
arxiv_search ┘
  │
  ├── [sufficient OR iteration >= 3] ──► generate_report ──► END
  │
  └── [not sufficient] ──────────────────────────────────────► plan_searches
```

## Why parallel tool execution

Web search and arxiv search are independent. Running them in parallel halves the latency. LangGraph's `Send` API handles fan-out and join natively — this is one of the patterns that makes LangGraph better than plain chains for tool-using agents.

## What makes this portfolio-worthy

A naive implementation just does one search and generates. This agent:
1. Plans its searches strategically
2. Runs multiple source types in parallel
3. Self-evaluates whether it has enough information
4. Loops to fill gaps before generating
5. Produces fully structured, cited output

That is a real agentic workflow, not a glorified API call.
