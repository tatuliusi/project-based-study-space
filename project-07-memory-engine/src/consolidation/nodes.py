from __future__ import annotations

import asyncio
import os

import numpy as np
from langchain_openai import ChatOpenAI
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.consolidation.state import ConsolidationState
from src.models import Episode, SemanticMemory
from src.services.embedding_service import embed, embed_batch
from src.services.postgres_service import PostgresService
from src.services.qdrant_service import QdrantService

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

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

MIN_CLUSTER_SIZE = 3
MAX_K = 10


async def load_old_episodes(state: ConsolidationState) -> dict:
    episodes = await _postgres.get_old_episodes(state["user_id"], days=30)
    return {"old_episodes": episodes}


async def cluster_similar(state: ConsolidationState) -> dict:
    episodes: list[Episode] = state["old_episodes"]

    if len(episodes) < MIN_CLUSTER_SIZE:
        return {"clusters": []}

    texts = [f"{e.event_type} {e.subject}: {e.detail}" for e in episodes]
    embeddings = await embed_batch(texts)
    X = np.array(embeddings)

    best_k, best_score = 2, -1.0
    for k in range(2, min(MAX_K, len(episodes))):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score, best_k = score, k

    km = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    id_by_index = {i: episodes[i].id for i in range(len(episodes))}
    clusters: list[list[str]] = [[] for _ in range(best_k)]
    for i, label in enumerate(labels):
        clusters[label].append(id_by_index[i])

    # Only keep clusters large enough to be worth summarising
    clusters = [c for c in clusters if len(c) >= MIN_CLUSTER_SIZE]
    return {"clusters": clusters}


async def merge_clusters(state: ConsolidationState) -> dict:
    episodes: list[Episode] = state["old_episodes"]
    clusters: list[list[str]] = state.get("clusters", [])

    if not clusters:
        return {"merged_memories": [], "merged_episode_ids": []}

    ep_by_id = {e.id: e for e in episodes}
    user_id = state["user_id"]
    merged_memories: list[SemanticMemory] = []
    merged_episode_ids: list[str] = []

    for cluster_ids in clusters:
        cluster_eps = [ep_by_id[eid] for eid in cluster_ids if eid in ep_by_id]
        if not cluster_eps:
            continue

        bullet_list = "\n".join(
            f"- [{e.occurred_at.date()}] {e.event_type.replace('_', ' ')} {e.subject}: {e.detail}"
            for e in cluster_eps
        )
        prompt = (
            "Summarise these related episodes into a single concise fact about the user "
            "(one sentence, written as a timeless belief or characteristic):\n\n"
            f"{bullet_list}"
        )
        summary_msg = await _llm.ainvoke(prompt)
        summary_text = summary_msg.content.strip()

        embedding = await embed(summary_text)
        mem = SemanticMemory(
            user_id=user_id,
            content=summary_text,
            embedding=embedding,
            importance=0.8,
        )
        merged_memories.append(mem)
        merged_episode_ids.extend(cluster_ids)

    return {
        "merged_memories": merged_memories,
        "merged_episode_ids": merged_episode_ids,
    }


async def write_summaries(state: ConsolidationState) -> dict:
    for mem in state.get("merged_memories", []):
        await _qdrant.upsert(mem)
    return {}


async def prune_originals(state: ConsolidationState) -> dict:
    ids = state.get("merged_episode_ids", [])
    if ids:
        await _postgres.delete_episodes(ids)
    return {}
