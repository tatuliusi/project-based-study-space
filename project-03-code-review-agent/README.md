# Project 3 — Automated Code Review Agent

A LangGraph-based agent that reviews a GitHub pull request from a PR URL or reference, inspects the diff, and produces a structured review with verdict, summary, and prioritized findings.

This is a strong example of a multi-agent workflow where specialist reviewers work in parallel and a supervisor synthesizes the results into one final decision.

## What this project demonstrates

- LangGraph supervisor / worker orchestration
- Parallel execution with the `Send` API
- GitHub pull request diff fetching and parsing
- Specialized reviewer prompts for security, logic, and style
- Structured outputs using Pydantic v2
- A clean CLI for running reviews locally

## Tech stack

- **LangGraph** — orchestration and graph control flow
- **GitHub REST API** — fetches PR metadata and diff payloads
- **OpenAI** — `gpt-4o-mini` for specialist workers and `gpt-4o` for the final synthesis
- **Pydantic v2** — validated review and finding schemas
- **Python CLI** — local execution and formatted terminal output

## Quick start

1. Create a virtual environment and install dependencies:

```bash
cd project-03-code-review-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the environment template and add your keys:

```bash
cp .env.example .env
```

Then set:

- `OPENAI_API_KEY`
- `GITHUB_TOKEN`

3. Run the review agent against a pull request:

```bash
python src/main.py --pr "owner/repo/123"
```

You can also pass a full GitHub PR URL:

```bash
python src/main.py --pr "https://github.com/owner/repo/pull/123"
```

Or return raw JSON:

```bash
python src/main.py --pr "owner/repo/123" --json
```

## Project layout

```text
project-03-code-review-agent/
├── src/
│   ├── github_client.py   # GitHub API helpers for diff retrieval
│   ├── graph.py           # LangGraph graph definition and dispatch logic
│   ├── main.py            # CLI entrypoint and terminal formatting
│   ├── nodes.py           # Worker agents and supervisor synthesis
│   ├── schemas.py         # Pydantic models for findings and review output
│   ├── state.py           # Typed graph state
│   └── __init__.py
├── .env.example
├── requirements.txt
├── README.md
├── ARCHITECTURE.md
└── .venv/
```

## Graph overview

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
dispatch to security_agent, logic_agent, style_agent
  │
  ├──► security_agent ──┐
  ├──► logic_agent ─────┼──► generate_review ──► END
  └──► style_agent ─────┘
```

Each specialist agent reviews the same PR diff but focuses on a different class of risk or maintainability issue. After all three workers finish, the supervisor merges their findings into a final `CodeReview` object.

## Why this matters

This pattern is useful when a single model is too broad or inconsistent for a domain-specific review. The project shows how to split responsibilities by expertise, run them concurrently, and then combine them into a deterministic final decision with clear prioritization.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design, state model, and graph-level implementation details.
