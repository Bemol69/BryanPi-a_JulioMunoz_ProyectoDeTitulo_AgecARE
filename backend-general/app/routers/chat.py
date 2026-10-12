"""Chat dentro de la aplicación entre una familia y una cuidadora. Los mensajes se eliminan
solos a los 7 días (ver app/chat_retention.py)."""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import or_, select

from app import models
from app.chat_retention import purge_expired
from app.deps import CurrentUser, Db
from app.errors import forbidden, not_found
from app.schemas.chat import (RETENTION_DAYS, ChatDetailOut, ChatLastMessageOut, ChatMessageIn,
                              ChatMessageOut, ChatStartIn, ChatSummaryOut)
from app.schemas.common import Page
from app.security import now_utc

router = APIRouter(prefix="/chats", tags=["Chat"])


def _other(conv: models.ChatConversation, me: models.User):
    """Datos de la otra persona de la conversación, vistos desde `me`."""
    if me.id == conv.family_user_id:
        cg = conv.caregiver
        return cg.user.full_name, cg.user.avatar_url, cg.id
    return conv.family.full_name, conv.family.avatar_url, None


def _is_participant(conv: models.ChatConversation, me: models.User) -> bool:
    return me.id == conv.family_user_id or me.id == conv.caregiver.user_id


def _msg_out(m: models.ChatMessage, me: models.User) -> ChatMessageOut:
    return ChatMessageOut(message_id=m.id, body=m.body, mine=m.sender_user_id == me.id,
                          created_at=m.created_at,
                          expires_at=m.created_at + timedelta(days=RETENTION_DAYS))


async def get_or_create_conversation(db: Db, profile: models.CaregiverProfile,
                                     family: models.User) -> tuple[models.ChatConversation, bool]:
    conv = (await db.execute(select(models.ChatConversation).where(
        models.ChatConversation.caregiver_profile_id == profile.id,
        models.ChatConversation.family_user_id == family.id))).scalars().first()
    if conv is not None:
        return conv, False
    conv = models.ChatConversation(caregiver_profile_id=profile.id, family_user_id=family.id,
                                   last_message_at=now_utc())
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv, True


async def add_message(db: Db, conv: models.ChatConversation, sender: models.User,
                      body: str) -> models.ChatMessage:
    now = now_utc()
    msg = models.ChatMessage(conversation_id=conv.id, sender_user_id=sender.id, body=body.strip(),
                             created_at=now)
    db.add(msg)
    conv.last_message_at = now
    await db.flush()
    return msg


async def _conversation_for(db: Db, conv_id: UUID, user: models.User) -> models.ChatConversation:
    conv = await db.get(models.ChatConversation, conv_id)
    if conv is None:
        raise not_found("La conversación no existe o ya expiró.")
    if not _is_participant(conv, user):
        raise forbidden("No participas en esta conversación.")
    return conv


# ---------- Mis conversaciones ----------
@router.get("", response_model=Page[ChatSummaryOut])
async def list_chats(db: Db, user: CurrentUser):
    await purge_expired(db)
    stmt = (select(models.ChatConversation)
            .join(models.CaregiverProfile,
                  models.CaregiverProfile.id == models.ChatConversation.caregiver_profile_id)
            .where(or_(models.ChatConversation.family_user_id == user.id,
                       models.CaregiverProfile.user_id == user.id))
            .order_by(models.ChatConversation.last_message_at.desc()))
    convs = (await db.execute(stmt)).scalars().all()
    items = []
    for conv in convs:
        last = (await db.execute(select(models.ChatMessage)
                                 .where(models.ChatMessage.conversation_id == conv.id)
                                 .order_by(models.ChatMessage.created_at.desc()).limit(1))).scalars().first()
        name, photo, profile_id = _other(conv, user)
        items.append(ChatSummaryOut(
            conversation_id=conv.id, other_name=name, other_photo_url=photo, other_profile_id=profile_id,
            last_message=ChatLastMessageOut(body=last.body, mine=last.sender_user_id == user.id,
                                            created_at=last.created_at) if last else None,
            last_message_at=conv.last_message_at))
    return Page(items=items, total=len(items))


# ---------- Iniciar (o retomar) una conversación con una cuidadora ----------
@router.post("/start", response_model=ChatDetailOut, status_code=201)
async def start_chat(body: ChatStartIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede iniciar una conversación.")
    profile = await db.get(models.CaregiverProfile, body.profile_id)
    if profile is None or not profile.is_listed or profile.admin_status != "approved":
        raise not_found("El perfil solicitado no existe.")
    await purge_expired(db)
    conv, _ = await get_or_create_conversation(db, profile, user)
    await add_message(db, conv, user, body.message)
    return await get_chat(conv.id, db, user)


# ---------- Una conversación con sus mensajes ----------
@router.get("/{conversation_id}", response_model=ChatDetailOut)
async def get_chat(conversation_id: UUID, db: Db, user: CurrentUser):
    await purge_expired(db)
    conv = await _conversation_for(db, conversation_id, user)
    msgs = (await db.execute(select(models.ChatMessage)
                             .where(models.ChatMessage.conversation_id == conv.id)
                             .order_by(models.ChatMessage.created_at.asc()))).scalars().all()
    name, photo, profile_id = _other(conv, user)
    return ChatDetailOut(conversation_id=conv.id, other_name=name, other_photo_url=photo,
                         other_profile_id=profile_id, messages=[_msg_out(m, user) for m in msgs])


# ---------- Enviar un mensaje ----------
@router.post("/{conversation_id}/messages", response_model=ChatMessageOut, status_code=201)
async def send_message(conversation_id: UUID, body: ChatMessageIn, db: Db, user: CurrentUser):
    conv = await _conversation_for(db, conversation_id, user)
    msg = await add_message(db, conv, user, body.body)
    return _msg_out(msg, user)
