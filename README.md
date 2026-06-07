# AI Engineering Portfolio

## Projects

### 1. [RAG Q&A Agent](./project-01-rag-qa-agent/)
Upload documents, ask questions, get cited answers. Demonstrates retrieval-augmented generation with a LangGraph state graph including relevance grading and query rewriting.

### 2. [Multi-source Research Agent](./project-02-research-agent/)
Given a topic, the agent autonomously searches the web and academic sources, then synthesizes a structured report. Demonstrates tool use, agentic loops, and structured LLM output.

### 3. [Automated Code Review Agent](./project-03-code-review-agent/)
Points at a GitHub PR and runs parallel specialist agents (security, logic, style) coordinated by a supervisor. Demonstrates the supervisor/worker multi-agent pattern.

### 4. [Autonomous Data Analyst](./project-04-data-analyst-agent/)
Given a dataset, the agent iteratively writes and executes Python code, interprets results, and produces insights. Demonstrates code-generation loops and human-in-the-loop checkpointing.

### 5. [Production Customer Support System](./project-05-production-support/)
A triage agent routes conversations to specialist agents with full session memory, escalation to human agents, streaming responses, and a FastAPI backend. Demonstrates production LangGraph patterns.

### 6. [Scheduled Research-to-Report Pipeline](./project-06-research-pipeline/)
A topic fans out into parallel research branches via the LangGraph `Send` API, fact-checks claims, then renders a formatted PDF report — deliverable on-demand or on a cron schedule. Demonstrates parallel fan-out/fan-in and scheduled agentic pipelines.

### 7. [Semantic Memory & Personalization Engine](./project-07-memory-engine/)
A personal assistant with a three-tier memory system: semantic (Qdrant vectors), episodic (Postgres events), and a structured preference profile. A background consolidation agent merges and summarizes old memories nightly. Demonstrates production memory architecture for AI systems.

### 8. [LLM Evaluation & Quality Gate System](./project-08-eval-framework/)
Define eval datasets, run them against any LLM app, score outputs with LLM-as-judge and RAGAS-style metrics, detect regressions, and block CI deploys when quality drops. Demonstrates evaluation engineering and the LLM-as-judge pattern.

### 9. [Autonomous SWE Agent](./project-09-swe-agent/)
Given a GitHub issue, the agent reads the codebase, plans a fix, writes and tests code in a Docker sandbox, iterates until tests pass, and opens a pull request. Demonstrates long-horizon planning, sandboxed code execution, and GitHub tool use.

### 10. [Multi-Agent Collaborative Reasoning Swarm](./project-10-reasoning-swarm/)
A structured debate between four agents — Proposer, Critic, Devil's Advocate, Synthesizer — that run across multiple rounds to produce rigorous consensus answers. Built with composed LangGraph subgraphs and streamed over SSE. Demonstrates agent-to-agent communication and emergent reasoning.

## Tech stack

- **Orchestration:** LangGraph (graphs, subgraphs, Send API, interrupt)
- **LLM integrations:** Anthropic SDK, OpenAI SDK, LangChain
- **Structured output:** Pydantic v2
- **Vector stores:** FAISS, Chroma, Qdrant
- **APIs:** Tavily (search), GitHub REST API
- **Backend:** FastAPI (SSE, async, webhooks)
- **UI:** Streamlit
- **Persistence:** Postgres, Redis
- **Code execution:** Docker SDK (sandboxed)
- **Scheduling:** APScheduler

## Running any project

Each project is self-contained. See the project's own `README.md` for setup and run instructions.
