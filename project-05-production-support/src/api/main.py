import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool

from src.api.schemas import (
    ConversationOut,
    EscalateRequest,
    MessageOut,
    SendMessageRequest,
    StartConversationRequest,
    StartConversationResponse,
)
from src.db import close_pool, init_pool
from src.graph.graph import build_graph

load_dotenv()

_DATABASE_URL = os.environ["DATABASE_URL"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    await init_pool(_DATABASE_URL)

    pg_pool = AsyncConnectionPool(conninfo=_DATABASE_URL, kwargs={"autocommit": True})
    await pg_pool.open()
    checkpointer = AsyncPostgresSaver(pg_pool)
    await checkpointer.setup()

    app.state.graph = build_graph(checkpointer)
    app.state.pg_pool = pg_pool

    yield

    await close_pool()
    await pg_pool.close()


app = FastAPI(title="Production Support System", lifespan=lifespan)


# ---------------------------------------------------------------------------
# POST /conversations
# ---------------------------------------------------------------------------

@app.post("/conversations", response_model=StartConversationResponse)
async def start_conversation(body: StartConversationRequest):
    return StartConversationResponse(conversation_id=str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# POST /conversations/{id}/messages  (SSE streaming)
# ---------------------------------------------------------------------------

async def _stream_graph(graph, input_data, config) -> AsyncGenerator[str, None]:
    async for event in graph.astream_events(input_data, config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

    state = await graph.aget_state(config)
    if state and state.next:
        yield f"data: {json.dumps({'type': 'interrupted', 'waiting_for': list(state.next)})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, body: SendMessageRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": conversation_id}}

    state = await graph.aget_state(config)
    if state and state.next:
        raise HTTPException(
            status_code=409,
            detail="Conversation is awaiting human escalation. Use POST /conversations/{id}/escalate.",
        )

    existing = state.values if state else {}
    user_id = existing.get("user_id", "anonymous")

    if not existing.get("conversation_id"):
        # First message — provide full initial state
        input_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": [HumanMessage(content=body.content)],
            "category": None,
            "escalated": False,
            "agent_notes": "",
            "user_context": None,
        }
    else:
        input_data = {"messages": [HumanMessage(content=body.content)]}

    return StreamingResponse(
        _stream_graph(graph, input_data, config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /conversations/{id}/messages with user_id (conversation init)
# ---------------------------------------------------------------------------

@app.post("/conversations/{conversation_id}/init")
async def init_conversation(conversation_id: str, body: StartConversationRequest):
    """Attach a user_id to a conversation before the first message."""
    graph = app.state.graph
    config = {"configurable": {"thread_id": conversation_id}}

    state = await graph.aget_state(config)
    if state and state.values.get("conversation_id"):
        raise HTTPException(status_code=409, detail="Conversation already initialised.")

    # Persist bare state so user_id is stored in the checkpoint
    from langchain_core.messages import SystemMessage as _SM

    input_data = {
        "conversation_id": conversation_id,
        "user_id": body.user_id,
        "messages": [],
        "category": None,
        "escalated": False,
        "agent_notes": "",
        "user_context": None,
    }
    await graph.aupdate_state(config, input_data)
    return {"conversation_id": conversation_id, "user_id": body.user_id}


# ---------------------------------------------------------------------------
# GET /conversations/{id}
# ---------------------------------------------------------------------------

@app.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: str):
    graph = app.state.graph
    config = {"configurable": {"thread_id": conversation_id}}

    state = await graph.aget_state(config)
    if not state or not state.values.get("conversation_id"):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    v = state.values
    messages = [
        MessageOut(role=m.type, content=m.content)
        for m in v.get("messages", [])
        if hasattr(m, "content") and m.content
    ]

    return ConversationOut(
        conversation_id=conversation_id,
        user_id=v.get("user_id", ""),
        messages=messages,
        escalated=v.get("escalated", False),
        category=v.get("category"),
        interrupted=bool(state.next),
    )


# ---------------------------------------------------------------------------
# POST /conversations/{id}/escalate
# ---------------------------------------------------------------------------

@app.post("/conversations/{conversation_id}/escalate")
async def escalate(conversation_id: str, body: EscalateRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": conversation_id}}

    state = await graph.aget_state(config)
    if not state or not state.next:
        raise HTTPException(
            status_code=400,
            detail="Conversation is not awaiting escalation.",
        )

    return StreamingResponse(
        _stream_graph(graph, Command(resume=body.response), config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
