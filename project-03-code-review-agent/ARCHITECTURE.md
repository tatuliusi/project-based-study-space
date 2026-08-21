# Architecture — Automated Code Review Agent

## Core pattern: supervisor + specialist workers

This project uses a classic multi-agent pattern: one orchestrator delegates work to specialized reviewers, each focusing on a different risk class. The supervisor then reads the worker outputs and synthesizes a single final review.

The important design idea is that the workflow is not just three prompts in sequence. The three reviewer agents run concurrently against the same diff, and only after they finish does the synthesis step produce the final verdict.

## State model

```python
class ReviewState(TypedDict):
    pr_url: str
    diff: str
    file_summaries: list[FileSummary]
    security_findings: list[Finding]
    logic_findings: list[Finding]
    style_findings: list[Finding]
    final_review: CodeReview | None
```

The graph stores the original PR reference, the raw diff payload, per-file patch summaries, the findings from each specialist reviewer, and the final review.

```python
class Finding(BaseModel):
    severity: Literal["critical", "major", "minor", "info"]
    file: str
    line: int | None = None
    description: str
    suggestion: str
```

```python
class FileSummary(BaseModel):
    filename: str
    status: Literal["added", "modified", "removed"]
    patch: str
```

```python
class AgentFindings(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
```

```python
class CodeReview(BaseModel):
    verdict: Literal["approve", "request_changes", "comment"]
    summary: str
    priority_issues: list[Finding]
```

## Nodes

### `fetch_pr_diff`
Fetches the PR diff from the GitHub API using the repository owner, repo name, and PR number parsed from a URL or `owner/repo/123` format.

### `parse_diff`
Splits the unified diff into file-level sections, extracts a file summary per patch, and stores the relevant hunk text for each changed file.

### `security_agent`
Runs a security-focused prompt that looks for:

- SQL injection
- XSS and unsafe HTML rendering
- Hardcoded secrets
- Path traversal
- Missing auth checks
- Command injection
- Unsafe deserialization

### `logic_agent`
Runs a correctness-focused prompt for:

- Null/None dereferences
- Off-by-one mistakes
- Race conditions
- Incorrect branching logic
- Missing edge conditions
- Broken API usage

### `style_agent`
Runs a maintainability-focused prompt for:

- Naming issues
- Excessive complexity
- Duplication
- Weak typing
- Missing documentation
- Unclear functions or nested control flow

### `generate_review`
Uses a senior reviewer prompt to merge the specialist outputs and produce a final verdict, summary, and ranked `priority_issues` list.

## Graph definition

```python
def _dispatch(state: ReviewState) -> list[Send]:
    snapshot = dict(state)
    return [
        Send("security_agent", snapshot),
        Send("logic_agent", snapshot),
        Send("style_agent", snapshot),
    ]
```

```text
START
  │
  ▼
fetch_pr_diff
  │
  ▼
parse_diff
  │
  ▼
_dispatch → [security_agent, logic_agent, style_agent]
  │
  ├──► security_agent ──┐
  ├──► logic_agent ─────┼──► generate_review ──► END
  └──► style_agent ─────┘
```

This matches the actual implementation in `src/graph.py`: the graph triggers the three worker agents in parallel, then merges them by routing all of them into the final synthesis node.

## Why the join matters

The most technically important part of this design is the transition from parallel workers to a single synthesis node. The state fields are accumulated across agents, and the supervisor does not run until all reviews are available.

That is exactly the kind of coordination pattern LangGraph is designed for: a graph can branch, fan out, and synchronize work without manually managing threads or callback orchestration.

## Model routing strategy

The implementation uses two LLM tiers:

- **Worker models:** `gpt-4o-mini` for speed and lower cost across the review experts
- **Supervisor model:** `gpt-4o` for final synthesis and ranking

This is a pragmatic pattern for real agent systems: keep the expensive reasoning model limited to the highest-value step while using cheaper models for repetitive specialist work.

## Data flow in practice

1. The user provides a PR URL or `owner/repo/number`.
2. The app resolves the GitHub repo and retrieves the raw diff.
3. The diff is parsed into file patches.
4. Three worker agents review the same request with different lenses.
5. Each worker returns a list of `Finding` objects.
6. The supervisor combines them into one `CodeReview` with a verdict and summary.
7. The CLI prints the findings and final recommendation.

## Why this project is portfolio-worthy

This project shows more than a basic LLM wrapper. It demonstrates:

- multi-agent decomposition by responsibility
- state-based orchestration with LangGraph
- structured parsing and validation with Pydantic
- external API integration with GitHub
- cost-aware model routing
- output aggregation into a single production-style review

That combination makes it a strong example of practical agent engineering rather than a toy prompt demo.
