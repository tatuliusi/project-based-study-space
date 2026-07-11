from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from langchain_core.messages import HumanMessage

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    MemoryListResponse,
)
from src.config import settings
from src.graph.pipeline import turn_graph
from src.scheduler.jobs import create_scheduler
from src.services.postgres_service import PostgresService
from src.services.qdrant_service import QdrantService

_qdrant = QdrantService(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
)
_postgres = PostgresService(dsn=settings.postgres_dsn)
_scheduler = create_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _qdrant.ensure_collection()
    await _postgres.init_schema()
    _scheduler.start()
    yield
    _scheduler.shutdown(wait=False)


app = FastAPI(title="Memory Engine", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    turn_id = str(uuid4())
    initial_state = {
        "user_id": req.user_id,
        "turn_id": turn_id,
        "messages": [HumanMessage(content=req.message)],
        "ranked_memories": [],
        "preference_profile": None,
        "extracted": None,
    }
    final_state = await turn_graph.ainvoke(initial_state)

    ai_messages = [
        m for m in final_state["messages"] if hasattr(m, "type") and m.type == "ai"
    ]
    reply = ai_messages[-1].content if ai_messages else ""

    return ChatResponse(
        reply=reply,
        memories_used=final_state.get("ranked_memories", []),
    )


@app.get("/users/{user_id}/memories", response_model=MemoryListResponse)
async def list_memories(user_id: str) -> MemoryListResponse:
    semantic = await _qdrant.get_all_for_user(user_id)
    profile = await _postgres.load_profile(user_id)
    return MemoryListResponse(semantic=semantic, profile=profile)


@app.delete("/users/{user_id}/memories/{memory_id}", status_code=204)
async def delete_memory(user_id: str, memory_id: str) -> None:
    await _qdrant.delete(memory_id)


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str) -> None:
    """Right to be forgotten — removes all data for the user."""
    memories = await _qdrant.get_all_for_user(user_id)
    for mem in memories:
        await _qdrant.delete(mem.id)
    episodes = await _postgres.get_recent_episodes(user_id, days=36500)
    if episodes:
        await _postgres.delete_episodes([e.id for e in episodes])


@app.post("/consolidate/{user_id}", status_code=202)
async def trigger_consolidation(user_id: str) -> dict:
    from src.consolidation.graph import consolidation_graph

    await consolidation_graph.ainvoke({"user_id": user_id})
    return {"status": "consolidation complete", "user_id": user_id}
