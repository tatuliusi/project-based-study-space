# Project 02 — Multi-source Research Agent

A lightweight research assistant built with LangGraph that plans searches, checks whether the answers are complete, fills gaps, and then produces a structured final report.

This project is a good example of an agent loop where the model does more than answer once: it decides what it still needs to know, searches again if necessary, and stops when the answer is strong enough.

## What this project demonstrates

- LangGraph orchestration with tool-based node execution
- Multi-step research planning and iterative search
- Self-evaluation of completeness before finalizing a response
- Conditional routing based on coverage gaps
- Pydantic v2 structured output for reliable report generation
- Streamlit-based local interface with a visible trace of the workflow

## Tech stack

- **LangGraph** — graph orchestration and control flow
- **Tavily API** — live web search for research grounding
- **OpenAI GPT-4o-mini** — planning, evaluation, and synthesis
- **Pydantic v2** — validated output models
- **Streamlit** — local app interface

## Setup

```bash
cd project-02-research-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then add your keys to `.env`:

- `OPENAI_API_KEY`
- `TAVILY_API_KEY`

You can get a free Tavily API key at https://tavily.com.

## Run locally

```bash
streamlit run src/app.py
```

## Agent flow

```text
START → plan → search → evaluate
  ↑ (missing information, iter < 3)   ↓ (sufficient or max iterations reached)
  └──────────────────────────────────────────── generate → END
```

The agent can run up to a few search cycles, filling in gaps before generating the final answer.

## More details

See [ARCHITECTURE.md](ARCHITECTURE.md) for the graph design, data flow, and implementation notes.
