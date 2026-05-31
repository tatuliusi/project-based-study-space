# Project 4 — Autonomous Data Analyst

Given a CSV or database, the agent writes Python code, executes it in a sandbox, reads the output, writes more code, and produces data insights and visualizations — all autonomously.

## What this demonstrates

- Code-generation + execution loop (the hardest agentic pattern)
- Safe sandboxed code execution
- Human-in-the-loop checkpointing with LangGraph
- Iterative reasoning — agent interprets output and decides what to analyze next
- Chart generation and interpretation

## Stack

- **LangGraph** — orchestration with checkpointing
- **RestrictedPython or subprocess sandbox** — safe code execution
- **pandas + matplotlib** — data manipulation and visualization
- **OpenAI** — code generation and interpretation (`gpt-4o`)
- **Pydantic v2** — structured analysis output

## Setup

```bash
cd project-04-data-analyst-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY to .env
```

## Run

```bash
python src/main.py --file data/sample.csv --question "What are the top 5 revenue drivers?"
```

## Graph overview

```
START → load_data → plan_analysis → generate_code → execute_code
      → [error] → fix_code → execute_code
      → [success] → interpret_results → [more_analysis] → plan_analysis
                                      → [done] → generate_report → END
```

See `ARCHITECTURE.md` for the full design.
