from __future__ import annotations

import os
from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from src.models import SemanticMemory

COLLECTION = os.getenv("QDRANT_COLLECTION", "semantic_memories")
VECTOR_SIZE = 1536  # text-embedding-3-small
DEDUP_THRESHOLD = 0.95


class QdrantService:
    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self._client = AsyncQdrantClient(host=host, port=port)

    async def ensure_collection(self) -> None:
        existing = {c.name for c in (await self._client.get_collections()).collections}
        if COLLECTION not in existing:
            await self._client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    async def upsert(self, memory: SemanticMemory) -> bool:
        """Insert memory if no near-duplicate exists. Returns True if inserted."""
        if await self._is_duplicate(memory.embedding, memory.user_id):
            return False

        point = PointStruct(
            id=memory.id,
            vector=memory.embedding,
            payload={
                "user_id": memory.user_id,
                "content": memory.content,
                "source_turn_id": memory.source_turn_id,
                "created_at": memory.created_at.isoformat(),
                "importance": memory.importance,
                "access_count": memory.access_count,
            },
        )
        await self._client.upsert(collection_name=COLLECTION, points=[point])
        return True

    async def search(
        self,
        embedding: list[float],
        user_id: str,
        top_k: int = 5,
    ) -> list[SemanticMemory]:
        results = await self._client.search(
            collection_name=COLLECTION,
            query_vector=embedding,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=top_k,
            with_payload=True,
        )
        memories = []
        for hit in results:
            p = hit.payload
            memories.append(
                SemanticMemory(
                    id=str(hit.id),
                    user_id=p["user_id"],
                    content=p["content"],
                    embedding=[],  # not returned to save bandwidth
                    source_turn_id=p.get("source_turn_id", ""),
                    importance=p.get("importance", 0.5),
                    access_count=p.get("access_count", 0),
                )
            )
        return memories

    async def delete(self, memory_id: str) -> None:
        await self._client.delete(
            collection_name=COLLECTION,
            points_selector=PointIdsList(points=[memory_id]),
        )

    async def get_all_for_user(self, user_id: str, limit: int = 1000) -> list[SemanticMemory]:
        results, _ = await self._client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=limit,
            with_vectors=True,
            with_payload=True,
        )
        memories = []
        for point in results:
            p = point.payload
            memories.append(
                SemanticMemory(
                    id=str(point.id),
                    user_id=p["user_id"],
                    content=p["content"],
                    embedding=list(point.vector),
                    source_turn_id=p.get("source_turn_id", ""),
                    importance=p.get("importance", 0.5),
                    access_count=p.get("access_count", 0),
                )
            )
        return memories

    async def _is_duplicate(self, embedding: list[float], user_id: str) -> bool:
        results = await self._client.search(
            collection_name=COLLECTION,
            query_vector=embedding,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=1,
            with_payload=False,
        )
        return bool(results and results[0].score >= DEDUP_THRESHOLD)
