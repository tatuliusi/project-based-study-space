# Project 9 — Autonomous SWE Agent

An agent that takes a GitHub issue, understands the codebase, plans a fix, writes and tests the code in an isolated Docker sandbox, iterates until tests pass, and opens a pull request.

## What this demonstrates

- Long-horizon multi-step planning: issue analysis → exploration → plan → implement → test → iterate
- Docker-sandboxed code execution: all code runs in an isolated container, never on the host
- File system tool use: read files, search the repo, write patches, run commands
- Test-driven iteration loop: run tests → analyze failures → patch → repeat until green
- GitHub integration: fork awareness, branch creation, diff generation, PR submission

## Stack

- **LangGraph** — orchestration of the full SWE pipeline
- **Docker SDK (docker-py)** — spawn and manage isolated execution sandboxes
- **GitHub REST API (PyGithub)** — repo access, branch management, PR creation
- **Tree-sitter** — syntax-aware code parsing for safe targeted edits
- **OpenAI** — planning agent + patch generation
- **Pydantic v2** — plan schema, tool call schemas, test result schemas

## Setup

```bash
cd project-09-swe-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY, GITHUB_TOKEN to .env
# Docker must be running locally

uvicorn src.api.main:app --reload
```

Run the test suite with `pytest tests/ -v` before starting the API.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Submit a GitHub issue URL; returns task ID |
| GET | `/tasks/{id}` | Get task status and current agent step |
| GET | `/tasks/{id}/plan` | Get the agent's implementation plan |
| GET | `/tasks/{id}/diff` | Get the final diff before PR is opened |
| POST | `/tasks/{id}/approve` | Human approval gate — trigger PR creation |
| GET | `/tasks/{id}/pr` | Get the opened PR URL |

## Graph overview

```
START
  │
  ▼
analyze_issue          (parse issue text, identify affected area, clarify ambiguities)
  │
  ▼
explore_repo           (list files, read relevant modules, build mental map)
  │
  ▼
create_plan            (structured N-step implementation plan with file targets)
  │
  ▼
implement              (generate patches for each planned change)
  │
  ▼
run_tests              (execute test suite in Docker sandbox)
  │
  ├── [tests pass] ──────────────────────────────┐
  │                                              │
  └── [tests fail] ──► analyze_failures          │
                             │                  │
                             ▼                  │
                        patch                   │
                             │                  │
                        run_tests ──────────────┘
                        (max 5 iterations)
  │
  ▼
human_approval         (HITL: show diff, wait for /approve)
  │
  ▼
open_pr                (create branch, commit, open PR with plan as description)
  │
  ▼
END
```

See `ARCHITECTURE.md` for the full design.
