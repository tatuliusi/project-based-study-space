# Project 02 — Multi-source Research Agent

A LangGraph agent that researches any question by planning web searches, evaluating coverage, looping to fill gaps, and producing a Pydantic-structured report.

## What this demonstrates

- LangGraph tool nodes with real external APIs
- Self-evaluation loop — the agent decides when it has enough information
- Conditional routing based on coverage verdict
- Structured LLM output with Pydantic v2
- Iterative search with gap-filling across up to 3 iterations

## Stack

- **LangGraph** — graph orchestration with conditional loop
- **Tavily API** — real-time web search
- **OpenAI GPT-4o-mini** — planning, evaluation, and report generation
- **Pydantic v2** — structured output schemas
- **Streamlit** — UI with live trace sidebar

## Setup

```bash
cd project-02-research-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY and TAVILY_API_KEY to .env
```

Get a free Tavily API key at https://tavily.com.

## Run

```bash
streamlit run src/app.py
```

## Graph

```
START → plan → search → evaluate
  ↑ (gaps found, iter ≤ 3)    ↓ (sufficient OR iter > 3)
  └──────────────────────── generate → END
```

See `ARCHITECTURE.md` for the full design.
