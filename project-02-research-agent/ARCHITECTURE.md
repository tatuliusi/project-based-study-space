# Architecture — Multi-source Research Agent

## Core pattern: plan → search → self-evaluate loop

This agent has **agency over its own search strategy**. It decides what to search, evaluates what it found, and decides whether to search more or stop. Project 1 was a fixed retrieve-grade-generate pipeline. This project introduces a real agentic loop with conditional routing.

## Implementation entry point

The planning loop and conditional routing are implemented in `src/graph.py`.

## State

```python
class ResearchState(TypedDict):
    query: str
    planned_queries: list[str]       # queries for this iteration
    search_results: list[dict]       # accumulated across all iterations
    iteration: int                   # loop guard (max 3)
    coverage_verdict: CoverageVerdict
    report: ResearchReport
    trace: ResearchTrace
```

## Schemas (Pydantic v2)

```python
class CoverageVerdict(BaseModel):
    sufficient: bool
    gaps: list[str]        # missing angles to search next iteration
    confidence: float      # 0.0–1.0

class Citation(BaseModel):
    title: str
    url: str
    snippet: str

class Finding(BaseModel):
    point: str
    sources: list[Citation]

class ResearchReport(BaseModel):
    title: str
    summary: str
    key_findings: list[Finding]
    sources: list[Citation]
    conclusion: str
```

## Nodes

### `plan`
LLM node. Iteration 1: plans 3–5 queries from scratch. Subsequent iterations: targets the `gaps` list from the previous `CoverageVerdict` to fill missing angles.

### `search`
Tool node. Calls Tavily API for each planned query. Accumulates results across iterations — results are never discarded, they stack.

### `evaluate`
LLM node with structured output. Reviews all accumulated results against the original query. Returns `CoverageVerdict`. Increments `iteration` counter.

### `generate`
LLM node with structured output. Reads all accumulated results and produces a `ResearchReport`. Only reached once coverage is sufficient or the loop guard fires.

## Graph

```
START
  │
  ▼
plan ──► search ──► evaluate
  ▲                    │
  │    [insufficient   │  [sufficient OR iteration > 3]
  │     AND iter ≤ 3]  │
  └────────────────────┤
                       ▼
                    generate ──► END
```

## Routing logic

```python
def route_after_evaluate(state) -> str:
    verdict = state["coverage_verdict"]
    iteration = state["iteration"]
    if not verdict or verdict.sufficient or iteration > 3:
        return "generate"
    return "plan"
```

The loop guard (`iteration > 3`) prevents infinite loops when the LLM never declares coverage sufficient.

## Key differences from Project 1

| Project 1 (RAG) | Project 2 (Research) |
|-----------------|----------------------|
| Fixed pipeline | Conditional loop |
| Grading is binary per-chunk | Self-evaluation of full coverage |
| Static document set | Dynamic: agent grows its own knowledge base |
| One LLM call path | Multiple LLM calls with gap-filling |
| Structured output: string | Structured output: nested Pydantic model |

## What makes this portfolio-worthy

A naive implementation does one search and generates. This agent:
1. Plans searches strategically
2. Self-evaluates whether it has enough information
3. Loops to fill specific identified gaps
4. Accumulates knowledge across iterations
5. Produces a fully structured, cited report via Pydantic

That is a real agentic workflow with genuine decision-making, not a glorified API call.
