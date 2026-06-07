# Project 10 — Multi-Agent Collaborative Reasoning Swarm

A structured debate system where multiple specialist agents — Proposer, Critic, Devil's Advocate, and Synthesizer — collaborate through rounds of argumentation to produce rigorous, well-reasoned answers to complex questions.

## What this demonstrates

- Agent-to-agent communication: agents read each other's prior outputs and respond to them
- Structured debate protocol: defined rounds (propose → critique → rebut → synthesize)
- Confidence-weighted consensus: Synthesizer weighs positions by agent-assigned confidence
- Swarm emergence: the final answer is better than any single agent could produce alone
- Multi-graph composition: each debate round is a subgraph, outer graph manages round orchestration

## Stack

- **LangGraph** — outer debate orchestration graph + per-round subgraphs
- **FastAPI** — REST API for question submission and debate streaming
- **Postgres** — full debate history with per-turn agent positions
- **OpenAI** — four distinct agent personas with role-specific system prompts
- **Pydantic v2** — position schemas, round schemas, consensus schemas
- **SSE** — stream debate turns to clients in real time

## Setup

```bash
cd project-10-reasoning-swarm
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY, DATABASE_URL to .env

docker compose up -d db
python src/db/migrate.py

uvicorn src.api.main:app --reload
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/debates` | Submit a question; returns debate ID |
| GET | `/debates/{id}/stream` | SSE stream of debate turns as they happen |
| GET | `/debates/{id}` | Full debate history and final consensus |
| GET | `/debates/{id}/consensus` | Only the final synthesized answer |
| POST | `/debates/{id}/challenge` | Human challenges the consensus; triggers a new round |

## Graph overview

**Outer orchestration graph:**
```
START
  │
  ▼
initialize_debate      (parse question, assign agent roles, set round limit)
  │
  ▼
run_round              (invoke per-round subgraph; append results to history)
  │
  ├── [consensus_reached or max_rounds] ──► synthesize_final ──► END
  │
  └── [disagreement] ──────────────────────► run_round  (next round)
```

**Per-round subgraph:**
```
proposer ──► critic ──► devil_advocate ──► rebuttal(proposer) ──► round_summary
```

Each agent reads the full transcript of the current round before writing its turn.

See `ARCHITECTURE.md` for the full design.
