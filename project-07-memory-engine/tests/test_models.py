"""Unit tests for Pydantic model validation — no LLM or DB required."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import (
    Episode,
    ExtractedEpisode,
    ExtractedFact,
    ExtractedMemories,
    PreferenceProfile,
    PreferenceUpdate,
    RankedMemory,
    SemanticMemory,
)


# ── ExtractedFact ────────────────────────────────────────────────────────────

def test_extracted_fact_default_importance():
    f = ExtractedFact(content="User likes Python")
    assert f.importance == 0.5


def test_extracted_fact_rejects_importance_above_one():
    with pytest.raises(ValidationError):
        ExtractedFact(content="x", importance=1.1)


def test_extracted_fact_rejects_negative_importance():
    with pytest.raises(ValidationError):
        ExtractedFact(content="x", importance=-0.1)


# ── ExtractedEpisode ─────────────────────────────────────────────────────────

def test_extracted_episode_rejects_bad_event_type():
    with pytest.raises(ValidationError):
        ExtractedEpisode(event_type="laughed_at", subject="Python", detail="...")


def test_extracted_episode_sentiment_bounds():
    with pytest.raises(ValidationError):
        ExtractedEpisode(event_type="mentioned", subject="x", detail="x", sentiment=1.5)
    with pytest.raises(ValidationError):
        ExtractedEpisode(event_type="mentioned", subject="x", detail="x", sentiment=-1.5)


def test_extracted_episode_valid_sentiments():
    for val in (-1.0, 0.0, 1.0):
        ep = ExtractedEpisode(event_type="decided", subject="x", detail="x", sentiment=val)
        assert ep.sentiment == val


# ── SemanticMemory ───────────────────────────────────────────────────────────

def test_semantic_memory_auto_id():
    m1 = SemanticMemory(user_id="u1", content="fact A")
    m2 = SemanticMemory(user_id="u1", content="fact B")
    assert m1.id != m2.id


def test_semantic_memory_embedding_defaults_empty():
    m = SemanticMemory(user_id="u1", content="fact")
    assert m.embedding == []


# ── Episode ──────────────────────────────────────────────────────────────────

def test_episode_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        Episode(user_id="u1", event_type="unknown", subject="x", detail="x")


def test_episode_valid_event_types():
    for et in ("asked_about", "complained_about", "mentioned", "decided"):
        ep = Episode(user_id="u1", event_type=et, subject="x", detail="x")
        assert ep.event_type == et


# ── PreferenceProfile ────────────────────────────────────────────────────────

def test_preference_profile_defaults():
    p = PreferenceProfile(user_id="u1")
    assert p.communication_style == "concise"
    assert p.topics_of_interest == []
    assert p.known_context == {}


def test_preference_profile_rejects_bad_style():
    with pytest.raises(ValidationError):
        PreferenceProfile(user_id="u1", communication_style="robotic")


# ── PreferenceUpdate ─────────────────────────────────────────────────────────

def test_preference_update_all_optional():
    u = PreferenceUpdate()
    assert u.communication_style is None
    assert u.topics_of_interest == []
    assert u.known_context == {}


# ── RankedMemory ─────────────────────────────────────────────────────────────

def test_ranked_memory_rejects_bad_source():
    with pytest.raises(ValidationError):
        RankedMemory(content="x", score=0.9, source="unknown")


def test_ranked_memory_valid_sources():
    for src in ("semantic", "episodic", "profile"):
        r = RankedMemory(content="x", score=0.5, source=src)
        assert r.source == src


# ── ExtractedMemories ────────────────────────────────────────────────────────

def test_extracted_memories_empty_defaults():
    em = ExtractedMemories()
    assert em.facts == []
    assert em.episodes == []
    assert em.preference_update.communication_style is None
