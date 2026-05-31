# Architecture — Automated Code Review Agent

## Core pattern: Supervisor / Worker

One supervisor agent coordinates multiple specialist worker agents. The supervisor dispatches work, collects results, and synthesizes. Workers run in parallel and have no knowledge of each other.

This is the most important multi-agent pattern to know for AI engineering interviews.

## State

```python
class ReviewState(TypedDict):
    pr_url: str
    diff: str                            # Raw git diff from GitHub API
    file_summaries: list[FileSummary]    # Per-file context for agents
    security_findings: list[Finding]
    logic_findings: list[Finding]
    style_findings: list[Finding]
    final_review: CodeReview | None
```

```python
class Finding(BaseModel):
    severity: Literal["critical", "major", "minor", "info"]
    file: str
    line: int | None
    description: str
    suggestion: str
```

## Agents

### Supervisor
Orchestrates the workflow. After receiving all worker findings, synthesizes them into a `CodeReview` with:
- Overall verdict (`approve`, `request_changes`, `comment`)
- Priority-ranked finding list
- Summary paragraph

### Security Agent
Specialist prompt focused on: SQL injection, XSS, hardcoded secrets, unsafe deserialization, dependency vulnerabilities, auth/authz bypass patterns.

### Logic Agent
Specialist prompt focused on: off-by-one errors, null/None handling, race conditions, incorrect algorithm implementation, edge cases in business logic.

### Style Agent
Specialist prompt focused on: naming conventions, function length, duplication, missing error handling at boundaries, type annotation completeness.

## Graph

```
START
  │
  ▼
fetch_pr_diff  (GitHub API call)
  │
  ▼
parse_diff  (split into per-file summaries)
  │
  ▼
supervisor  (dispatch decision)
  │
  ├── Send(security_agent, file_summaries)  ──┐
  ├── Send(logic_agent, file_summaries)     ──┼──► collect_findings
  └── Send(style_agent, file_summaries)    ──┘         │
                                                        ▼
                                                   generate_review
                                                        │
                                                        ▼
                                                       END
```

## Why this pattern is hard to get right

The tricky part is the join: after three parallel agents finish, you need to collect all their results before the supervisor can run. LangGraph handles this with the `Send` API and a reducer function on the state list fields. Understanding reducers is the key LangGraph concept this project teaches.

## Model routing

Workers use `gpt-4o-mini` (fast, cheap). The supervisor uses `gpt-4o` (better at synthesis and judgment). This is a real production cost-optimization pattern — only spend money on the expensive model where it matters.
