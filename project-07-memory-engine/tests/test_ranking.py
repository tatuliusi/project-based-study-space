"""Unit tests for memory ranking logic — no LLM or DB required."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.graph.ranking import rank_memories
from src.models import Episode, PreferenceProfile, SemanticMemory


def _mem(content: str, importance: float = 0.5, age_days: int = 0) -> SemanticMemory:
    return SemanticMemory(
        user_id="u1",
        content=content,
        importance=importance,
        created_at=datetime.utcnow() - timedelta(days=age_days),
    )


def _episode(subject: str, age_days: int = 1) -> Episode:
    return Episode(
        user_id="u1",
        event_type="mentioned",
        subject=subject,
        detail=f"User mentioned {subject}",
        occurred_at=datetime.utcnow() - timedelta(days=age_days),
    )


def test_profile_facts_always_included():
    profile = PreferenceProfile(
        user_id="u1",
        communication_style="concise",
        topics_of_interest=["Python"],
    )
    ranked = rank_memories([], [], profile, top_k=10)
    contents = [r.content for r in ranked]
    assert any("concise" in c for c in contents)
    assert any("Python" in c for c in contents)


def test_semantic_score_beats_old_episode():
    recent_mem = _mem("Python is my main language", importance=0.9, age_days=0)
    old_ep = _episode("Python", age_days=29)

    ranked = rank_memories([(recent_mem, 0.95)], [old_ep], None, top_k=5)
    semantic_idx = next(i for i, r in enumerate(ranked) if r.source == "semantic")
    episodic_idx = next(i for i, r in enumerate(ranked) if r.source == "episodic")
    assert semantic_idx < episodic_idx, "High-similarity recent memory should outrank old episode"


def test_top_k_respected():
    mems = [(_mem(f"fact {i}", importance=0.5, age_days=i), 0.8) for i in range(20)]
    ranked = rank_memories(mems, [], None, top_k=3)
    assert len(ranked) == 3


def test_empty_inputs_returns_empty():
    ranked = rank_memories([], [], None, top_k=5)
    assert ranked == []
