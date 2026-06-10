from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.models import ExtractedMemories, PreferenceProfile, RankedMemory


class TurnState(TypedDict):
    user_id: str
    turn_id: str

    messages: Annotated[list[BaseMessage], add_messages]

    # populated by retrieve_memories
    ranked_memories: list[RankedMemory]
    preference_profile: PreferenceProfile | None

    # populated by extract_memories
    extracted: ExtractedMemories | None
