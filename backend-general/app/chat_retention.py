"""Los chats se limpian solos: todo mensaje (y solicitud de contacto) con más de 7 días se
elimina. En Vercel no hay un proceso permanente, así que la limpieza se hace al usar el chat,
pero como mucho una vez cada pocos minutos por instancia: antes eran 3 consultas DELETE en cada visita."""
import time
from datetime import timedelta

from sqlalchemy import delete, exists, select

from app import models
from app.schemas.chat import RETENTION_DAYS
from app.security import now_utc


PURGE_EVERY_SECONDS = 300
_last_purge = float("-inf")


async def purge_expired(db, *, force: bool = False) -> None:
    global _last_purge
    if not force and time.monotonic() - _last_purge < PURGE_EVERY_SECONDS:
        return
    _last_purge = time.monotonic()
    cutoff = now_utc() - timedelta(days=RETENTION_DAYS)
    await db.execute(delete(models.ChatMessage).where(models.ChatMessage.created_at < cutoff))
    has_messages = exists().where(models.ChatMessage.conversation_id == models.ChatConversation.id)
    await db.execute(delete(models.ChatConversation)
                     .where(models.ChatConversation.last_message_at < cutoff, ~has_messages))
    await db.execute(delete(models.ContactRequest).where(models.ContactRequest.created_at < cutoff))
