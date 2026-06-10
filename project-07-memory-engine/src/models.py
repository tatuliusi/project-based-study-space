from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _uid() -> str:
    return str(uuid4())


# ── Tier 1: Semantic memory (Qdrant) ────────────────────────────────────────

class SemanticMemory(BaseModel):
    id: str = Field(default_factory=_uid)
    user_id: str
    content: str
    embedding: list[float] = Field(default_factory=list)
    source_turn_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    importance: float = 0.5
    access_count: int = 0


# ── Tier 2: Episodic memory (Postgres) ──────────────────────────────────────

class Episode(BaseModel):
    id: str = Field(default_factory=_uid)
    user_id: str
    event_type: Literal["asked_about", "complained_about", "mentioned", "decided"]
    subject: str
    detail: str
    sentiment: float = 0.0   # -1.0 to 1.0
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


# ── Tier 3: Preference profile (Postgres) ───────────────────────────────────

class PreferenceProfile(BaseModel):
    user_id: str
    communication_style: Literal["concise", "detailed", "casual", "formal"] = "concise"
    topics_of_interest: list[str] = Field(default_factory=list)
    topics_to_avoid: list[str] = Field(default_factory=list)
    known_context: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── LLM extraction schema ────────────────────────────────────────────────────

class ExtractedFact(BaseModel):
    content: str
    importance: float = Field(ge=0.0, le=1.0, default=0.5)


class ExtractedEpisode(BaseModel):
    event_type: Literal["asked_about", "complained_about", "mentioned", "decided"]
    subject: str
    detail: str
    sentiment: float = Field(ge=-1.0, le=1.0, default=0.0)


class PreferenceUpdate(BaseModel):
    communication_style: Literal["concise", "detailed", "casual", "formal"] | None = None
    topics_of_interest: list[str] = Field(default_factory=list)
    topics_to_avoid: list[str] = Field(default_factory=list)
    known_context: dict[str, str] = Field(default_factory=dict)


class ExtractedMemories(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)
    episodes: list[ExtractedEpisode] = Field(default_factory=list)
    preference_update: PreferenceUpdate = Field(default_factory=PreferenceUpdate)


# ── Ranked memory for prompt injection ──────────────────────────────────────

class RankedMemory(BaseModel):
    content: str
    score: float
    source: Literal["semantic", "episodic", "profile"]
