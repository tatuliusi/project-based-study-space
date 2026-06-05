from pydantic import BaseModel


class StartConversationRequest(BaseModel):
    user_id: str


class StartConversationResponse(BaseModel):
    conversation_id: str


class SendMessageRequest(BaseModel):
    content: str


class EscalateRequest(BaseModel):
    response: str


class MessageOut(BaseModel):
    role: str
    content: str


class ConversationOut(BaseModel):
    conversation_id: str
    user_id: str
    messages: list[MessageOut]
    escalated: bool
    category: str | None
    interrupted: bool
