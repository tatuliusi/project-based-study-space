# Project 2 — Multi-source Research Agent

Given a topic, the agent autonomously searches the web and academic sources, synthesizes findings, and produces a structured report with citations.

## What this demonstrates

- LangGraph tool nodes with real external APIs
- Agentic loops — the agent decides when it has enough information to stop searching
- Structured LLM output with Pydantic v2
- Parallel tool invocation (web search + arxiv simultaneously)
- Conditional routing based on information sufficiency

## Stack

- **LangGraph** — orchestration
- **Tavily API** — web search
- **arxiv API** — academic paper retrieval
- **OpenAI** — reasoning and report generation (`gpt-4o`)
- **Pydantic v2** — structured report schema

## Setup

```bash
cd project-02-research-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY and TAVILY_API_KEY to .env
```

## Run

```bash
python src/main.py --topic "LangGraph multi-agent systems"
```

## Graph overview

```
START → plan_searches → [web_search, arxiv_search] → evaluate_coverage
      → [sufficient] → generate_report → END
      → [insufficient] → plan_searches (loop)
```

See `ARCHITECTURE.md` for the full design.
