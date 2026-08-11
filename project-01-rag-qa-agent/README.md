# Project 1 — RAG Q&A Agent

A lightweight document Q&A system implemented with LangGraph. Drop in PDFs or text files, the agent ingests them into a local vector store, and answers user questions with concise responses and source citations.

Key features

- Retrieval-Augmented Generation (RAG) pipeline with LangGraph orchestration
- Relevance grading to verify retrieved passages before generation
- Automatic query rewriting and retry when initial results are irrelevant
- Source citation for every answer

Tech stack

- **LangGraph** — orchestration and state management
- **FAISS** — local vector store for document embeddings
- **OpenAI** — embeddings and generation (configured via `.env`)
- **LangChain** — document loaders and text splitters
- **Streamlit** — lightweight web UI

Quick start

1. Create a Python virtual environment and install dependencies:

```bash
cd project-01-rag-qa-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy and configure environment variables:

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and any other provider keys
```

3. (Optional) Add test documents to `docs/` or run the provided ingestion helper:

```bash
python -m src.retriever --ingest docs/
```

4. Start the Streamlit UI:

```bash
streamlit run src/app.py
```

Project layout

```
project-01-rag-qa-agent/
├── src/
│   ├── app.py            # Streamlit UI + entrypoint
│   ├── graph.py          # LangGraph state graph definition
│   ├── nodes.py          # Node implementations (retrieve, grade, generate, rewrite)
│   └── retriever.py      # Vector store setup and document ingestion helpers
├── docs/                 # Example documents for quick testing
├── requirements.txt
├── .env.example
├── README.md
└── ARCHITECTURE.md
```

Graph overview

```
START → retrieve → grade_relevance → [relevant] → generate → END
                                   → [not relevant] → rewrite_query → retrieve
```

Useful tips

- If answers are generic, increase the number of retrieved passages or tune the text splitter.
- Use `gpt-4o-mini` or another capable generator configured in `.env` for best results.
- Delete or recreate the FAISS index when changing embedding models.

Further reading

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full design diagram and `src/` for implementation details.

Questions or contributions

Open an issue or submit a PR with improvements. This project is intended as a learning demo and starting point for RAG agents.
