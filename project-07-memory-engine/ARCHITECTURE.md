# Architecture — Semantic Memory & Personalization Engine

## Why this project exists in the progression

Project 5 introduced per-session memory as a `user_context` blob. That is enough for a support system. A personal assistant needs memory that persists indefinitely, is queryable semantically, and actively improves over time. This project makes memory first-class.

## The three memory tiers

### Tier 1: Semantic memory (Qdrant)
What the user knows, believes, and has discussed — stored as vector embeddings.

```python
class SemanticMemory(BaseModel):
    id: str
    user_id: str
    content: str               # natural language fact/statement
    embedding: list[float]     # text-embedding-3-small (1536 dims)
    source_turn_id: str
    created_at: datetime
    importance: float          # 0.0–1.0, updated by consolidation
    access_count: int
```

Queried by cosine similarity at the start of each turn. Top-5 semantic memories are injected into the system prompt.

### Tier 2: Episodic memory (Postgres)
A timestamped log of significant events — what happened, when, and how the user reacted.

```python
class Episode(BaseModel):
    id: str
    user_id: str
    event_type: str            # "asked_about", "complained_about", "mentioned", "decided"
    subject: str               # extracted entity
    detail: str
    sentiment: float           # -1.0 to 1.0
    occurred_at: datetime
```

Queried by recency and event type. Recent relevant episodes (last 30 days) are included in the prompt.

### Tier 3: Preference profile (Postgres, single row per user)
Explicit, structured model of what the user likes, dislikes, and how they prefer to communicate.

```python
class PreferenceProfile(BaseModel):
    user_id: str
    communication_style: Literal["concise", "detailed", "casual", "formal"]
    topics_of_interest: list[str]
    topics_to_avoid: list[str]
    known_context: dict[str, str]   # arbitrary key/value facts about the user
    updated_at: datetime
```

This is updated incrementally — the `extract_memories` node detects explicit preferences ("I prefer short answers") and patches the profile.

## Per-turn graph

### retrieve_memories
Runs three parallel queries:
1. Qdrant cosine similarity on the current message embedding
2. Postgres episode lookup: recent episodes mentioning entities in current message
3. Load preference profile

Results are ranked by a combined score: semantic similarity × recency decay × importance.

### build_context
Assembles the top-K memories into a formatted context block injected before the user message:

```
[Memory Context]
- You prefer concise answers.
- Last week you were working on a FastAPI project and found CORS setup confusing.
- You have mentioned disliking verbose explanations.
```

### respond
Standard chat completion with the memory context in the system prompt.

### extract_memories
After the response, a second LLM call extracts:
- New facts stated by the user (→ semantic memory)
- Events mentioned (→ episodic memory)
- Explicit preferences stated (→ preference profile patch)

Uses structured output (Pydantic) to ensure valid extraction.

### write_memories
- Checks for near-duplicate semantic memories (cosine similarity > 0.95) before inserting — no duplicates
- Inserts new episodes
- Patches preference profile fields that changed

## Background consolidation graph

Runs on a nightly schedule via APScheduler.

```
load_old_episodes        (episodes > 30 days old)
       │
cluster_similar          (k-means on episode embeddings, k chosen by silhouette score)
       │
merge_clusters           (LLM summarizes each cluster into a single semantic memory)
       │
write_summaries          (insert merged summaries into Qdrant with high importance score)
       │
prune_originals          (delete the raw episodes that were merged, keep summary)
```

This prevents unbounded memory growth while preserving long-term knowledge.

## Forgetting

The `DELETE /users/{id}/memories/{mem_id}` endpoint hard-deletes from Qdrant and Postgres. This is the user's right to be forgotten — important for any personal data system.

## What an interviewer will ask about this

1. "How do you avoid memory bloat over time?" — Consolidation graph clusters and summarizes old episodic memories; near-duplicate semantic memories are skipped on insert; TTL importance decay deprioritizes stale facts.
2. "How do you rank which memories to include in the prompt?" — Combined score: semantic similarity (Qdrant score) × recency decay (exponential, half-life 7 days) × importance weight. Top-K by this score.
3. "How does preference extraction work?" — Structured LLM call after each response, with a Pydantic schema for `ExtractedMemories`. Only explicit preference statements trigger profile updates; inferred preferences are stored as semantic memories, not the profile.
4. "What's the difference between semantic and episodic memory here?" — Semantic = timeless facts and beliefs ("user prefers Python"). Episodic = timestamped events with sentiment ("on 2026-05-12, user was frustrated by a Postgres migration").
