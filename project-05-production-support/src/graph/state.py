from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    tier: Literal["free", "pro", "enterprise"] = "free"
    issue_history: list[str] = Field(default_factory=list)
    tone_notes: str = ""


class SupportState(TypedDict):
    conversation_id: str
    user_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    category: Literal["billing", "technical", "complaint", "unknown"] | None
    escalated: bool
    agent_notes: str
    user_context: UserContext | None
