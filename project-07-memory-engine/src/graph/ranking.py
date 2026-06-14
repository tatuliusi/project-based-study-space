from __future__ import annotations

import math
import os
from datetime import datetime, timezone

from src.models import Episode, PreferenceProfile, RankedMemory, SemanticMemory

SEMANTIC_W = float(os.getenv("SEMANTIC_SIMILARITY_WEIGHT", "0.5"))
RECENCY_W = float(os.getenv("RECENCY_WEIGHT", "0.3"))
IMPORTANCE_W = float(os.getenv("IMPORTANCE_WEIGHT", "0.2"))
HALF_LIFE_DAYS = float(os.getenv("RECENCY_HALF_LIFE_DAYS", "7"))
TOP_K = int(os.getenv("TOP_K_MEMORIES", "5"))


def _recency_decay(dt: datetime) -> float:
    age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    return math.exp(-math.log(2) * age_days / HALF_LIFE_DAYS)


def rank_memories(
    semantic_hits: list[tuple[SemanticMemory, float]],
    episodes: list[Episode],
    profile: PreferenceProfile | None,
    top_k: int = TOP_K,
) -> list[RankedMemory]:
    ranked: list[RankedMemory] = []

    for mem, sim_score in semantic_hits:
        recency = _recency_decay(mem.created_at)
        score = (
            SEMANTIC_W * sim_score
            + RECENCY_W * recency
            + IMPORTANCE_W * mem.importance
        )
        ranked.append(RankedMemory(content=mem.content, score=score, source="semantic"))

    for ep in episodes:
        recency = _recency_decay(ep.occurred_at)
        text = f"On {ep.occurred_at.date()}, you {ep.event_type.replace('_', ' ')} {ep.subject}: {ep.detail}"
        score = RECENCY_W * recency + 0.1
        ranked.append(RankedMemory(content=text, score=score, source="episodic"))

    if profile:
        profile_lines = []
        if profile.communication_style:
            profile_lines.append(f"You prefer {profile.communication_style} answers.")
        if profile.topics_of_interest:
            profile_lines.append(f"Topics you care about: {', '.join(profile.topics_of_interest)}.")
        if profile.topics_to_avoid:
            profile_lines.append(f"Topics to avoid: {', '.join(profile.topics_to_avoid)}.")
        for k, v in profile.known_context.items():
            profile_lines.append(f"{k}: {v}.")
        for line in profile_lines:
            ranked.append(RankedMemory(content=line, score=1.0, source="profile"))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:top_k]
