# AI Engineering Portfolio

Five progressively complex AI agent projects to show as a beginner.
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

## Tech stack

- **Orchestration:** LangGraph
- **LLM integrations:** LangChain, Anthropic SDK, OpenAI SDK
- **Structured output:** Pydantic v2
- **Vector stores:** FAISS, Chroma
- **APIs:** Tavily (search), GitHub REST API
- **Backend:** FastAPI
- **UI:** Streamlit
- **Persistence:** Postgres (Project 5)

## Running any project

Each project is self-contained. See the project's own `README.md` for setup and run instructions.
