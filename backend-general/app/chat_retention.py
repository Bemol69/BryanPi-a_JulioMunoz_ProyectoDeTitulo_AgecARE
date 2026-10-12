"""Los chats se limpian solos: todo mensaje (y solicitud de contacto) con más de 7 días se
elimina. En Vercel no hay un proceso permanente, así que la limpieza se hace al usar el chat."""
from datetime import timedelta

from sqlalchemy import delete, exists, select

from app import models
from app.schemas.chat import RETENTION_DAYS
from app.security import now_utc


async def purge_expired(db) -> None:
    cutoff = now_utc() - timedelta(days=RETENTION_DAYS)
    await db.execute(delete(models.ChatMessage).where(models.ChatMessage.created_at < cutoff))
    has_messages = exists().where(models.ChatMessage.conversation_id == models.ChatConversation.id)
    await db.execute(delete(models.ChatConversation)
                     .where(models.ChatConversation.last_message_at < cutoff, ~has_messages))
    await db.execute(delete(models.ContactRequest).where(models.ContactRequest.created_at < cutoff))
