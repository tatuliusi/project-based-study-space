from __future__ import annotations

from typing import TypedDict

from src.models import Episode, SemanticMemory


class ConsolidationState(TypedDict):
    user_id: str

    # loaded in load_old_episodes
    old_episodes: list[Episode]

    # produced by cluster_similar: list of episode-id clusters
    clusters: list[list[str]]

    # produced by merge_clusters: new semantic memories to persist
    merged_memories: list[SemanticMemory]

    # ids of raw episodes that were merged (for pruning)
    merged_episode_ids: list[str]
