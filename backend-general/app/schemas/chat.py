"""Esquemas del chat dentro de la aplicación (familia <-> cuidadora)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Los mensajes se eliminan automáticamente pasado este plazo (ver app/chat_retention.py).
RETENTION_DAYS = 7


class ChatStartIn(BaseModel):
    profile_id: UUID
    message: str = Field(min_length=1, max_length=1000)


class ChatMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class ChatMessageOut(BaseModel):
    message_id: UUID
    body: str
    mine: bool
    created_at: datetime
    expires_at: datetime


class ChatLastMessageOut(BaseModel):
    body: str
    mine: bool
    created_at: datetime


class ChatSummaryOut(BaseModel):
    conversation_id: UUID
    other_name: str
    other_photo_url: str | None
    other_profile_id: UUID | None  # solo cuando la otra persona es una cuidadora
    last_message: ChatLastMessageOut | None
    last_message_at: datetime


class ChatDetailOut(BaseModel):
    conversation_id: UUID
    other_name: str
    other_photo_url: str | None
    other_profile_id: UUID | None
    retention_days: int = RETENTION_DAYS
    messages: list[ChatMessageOut]
