# Project 3 — Automated Code Review Agent

Points at a GitHub pull request. Three specialist agents (security, logic, style) analyze the diff in parallel. A supervisor agent synthesizes the findings into a structured review.

## What this demonstrates

- LangGraph supervisor / worker multi-agent pattern
- Parallel agent execution with `Send` API
- GitHub REST API integration
- Role-specialized LLM prompting
- Structured multi-part output aggregation

## Stack

- **LangGraph** — supervisor graph + parallel worker subgraphs
- **GitHub REST API** — PR diff retrieval
- **OpenAI** — agent reasoning (`gpt-4o` for supervisor, `gpt-4o-mini` for workers)
- **Pydantic v2** — structured review output per agent

## Setup

```bash
cd project-03-code-review-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY and GITHUB_TOKEN to .env
```

## Run

```bash
python src/main.py --pr "owner/repo/123"
```

## Graph overview

```
START → fetch_pr_diff → supervisor
      → [dispatch] → security_agent ──┐
                   → logic_agent    ──┼──► supervisor → generate_review → END
                   → style_agent   ──┘
```

See `ARCHITECTURE.md` for the full design.
