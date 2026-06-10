from __future__ import annotations

from pydantic import BaseModel

from src.models import Episode, PreferenceProfile, RankedMemory, SemanticMemory


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    memories_used: list[RankedMemory]


class MemoryListResponse(BaseModel):
    semantic: list[SemanticMemory]
    profile: PreferenceProfile


class DeleteMemoryRequest(BaseModel):
    memory_id: str
