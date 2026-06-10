from __future__ import annotations

import asyncio
import os
import re
from uuid import uuid4

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.graph.ranking import rank_memories
from src.graph.state import TurnState
from src.models import Episode, ExtractedMemories, SemanticMemory
from src.services.postgres_service import PostgresService
from src.services.qdrant_service import QdrantService

_embedder = OpenAIEmbeddings(model="text-embedding-3-small")
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
_extractor = _llm.with_structured_output(ExtractedMemories)

_qdrant = QdrantService(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", "6333")),
)
_postgres = PostgresService(
    dsn=os.getenv(
        "POSTGRES_DSN",
        "postgresql+asyncpg://memory:memory@localhost:5432/memoryengine",
    )
)


async def retrieve_memories(state: TurnState) -> dict:
    user_id = state["user_id"]
    last_message = state["messages"][-1]
    text = last_message.content if hasattr(last_message, "content") else str(last_message)

    embedding, profile, episodes = await asyncio.gather(
        _embedder.aembed_query(text),
        _postgres.load_profile(user_id),
        _postgres.get_recent_episodes(user_id, days=30),
    )

    semantic_hits = await _qdrant.search(embedding, user_id, top_k=8)

    ranked = rank_memories(semantic_hits, episodes, profile)

    return {
        "ranked_memories": ranked,
        "preference_profile": profile,
    }


async def build_context(state: TurnState) -> dict:
    memories = state.get("ranked_memories", [])
    if not memories:
        return {}

    lines = [f"- {m.content}" for m in memories]
    context_block = "[Memory Context]\n" + "\n".join(lines)

    # Prepend the context block as a system message before the last user turn
    return {"messages": [SystemMessage(content=context_block)]}


async def respond(state: TurnState) -> dict:
    profile = state.get("preference_profile")
    style = profile.communication_style if profile else "concise"

    system = (
        f"You are a helpful personal assistant. Communication style: {style}. "
        "Use the [Memory Context] block (if present) to personalize your response."
    )

    history = [SystemMessage(content=system)] + state["messages"]
    response = await _llm.ainvoke(history)
    return {"messages": [response]}


async def extract_memories(state: TurnState) -> dict:
    user_id = state["user_id"]
    turn_id = state["turn_id"]

    # Gather user message + assistant response for extraction
    last_two = state["messages"][-2:]
    conversation_text = "\n".join(
        f"{'User' if not isinstance(m, AIMessage) else 'Assistant'}: {m.content}"
        for m in last_two
        if hasattr(m, "content")
    )

    prompt = (
        "Extract memory signals from this conversation exchange.\n\n"
        f"Conversation:\n{conversation_text}\n\n"
        "Return structured output with:\n"
        "- facts: timeless statements the user made about themselves (max 3)\n"
        "- episodes: concrete events mentioned (max 3)\n"
        "- preference_update: any explicit communication preferences stated"
    )

    extracted: ExtractedMemories = await _extractor.ainvoke(prompt)
    return {"extracted": extracted}


async def write_memories(state: TurnState) -> dict:
    user_id = state["user_id"]
    turn_id = state["turn_id"]
    extracted: ExtractedMemories | None = state.get("extracted")

    if not extracted:
        return {}

    tasks = []

    for fact in extracted.facts:
        embedding = await _embedder.aembed_query(fact.content)
        mem = SemanticMemory(
            user_id=user_id,
            content=fact.content,
            embedding=embedding,
            source_turn_id=turn_id,
            importance=fact.importance,
        )
        tasks.append(_qdrant.upsert(mem))

    for ep_data in extracted.episodes:
        ep = Episode(
            user_id=user_id,
            event_type=ep_data.event_type,
            subject=ep_data.subject,
            detail=ep_data.detail,
            sentiment=ep_data.sentiment,
        )
        tasks.append(_postgres.insert_episode(ep))

    if any([
        extracted.preference_update.communication_style,
        extracted.preference_update.topics_of_interest,
        extracted.preference_update.topics_to_avoid,
        extracted.preference_update.known_context,
    ]):
        tasks.append(
            _postgres.apply_preference_update(user_id, extracted.preference_update)
        )

    await asyncio.gather(*tasks)
    return {}
