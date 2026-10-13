"""Perfil profesional de la cuidadora: base de su ficha en el marketplace."""
from fastapi import APIRouter, File, Form, Request, UploadFile
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app import models, storage
from app.deps import CurrentUser, Db
from app.enums import CaregiverDocType
from app.errors import ApiError, conflict, forbidden, not_found
from app.schemas.common import Page
from app.schemas.marketplace import (CaregiverDocumentOut, CaregiverProfileOut,
                                     CaregiverProfilePatchIn, ContactMessageOut, EngagementOut,
                                     ReceivedHireRequestOut, ReviewOut)
from app.security import now_utc
from app.sync import fetch_admin_documents, sync_caregiver_to_admin, sync_document_to_admin

router = APIRouter(prefix="/caregiver", tags=["Perfil de cuidadora"])

DOCUMENT_CONTENT_TYPES = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


async def _is_engaged(db: Db, caregiver_profile_id) -> bool:
    active = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == caregiver_profile_id,
        models.CaregiverEngagement.status == "active"))).first()
    return active is not None


def _out(p: models.CaregiverProfile) -> CaregiverProfileOut:
    return CaregiverProfileOut(profile_id=p.id, headline=p.headline, bio=p.bio,
                               years_experience=p.years_experience, specialties=p.specialties or [],
                               languages=p.languages or [], zones=p.zones or [],
                               certifications=p.certifications or [], rating_avg=p.rating_avg,
                               reviews_count=p.reviews_count, is_listed=p.is_listed,
                               is_featured=p.is_featured, admin_status=p.admin_status)


async def _get_own_profile(db: Db, user: models.User) -> models.CaregiverProfile:
    if user.account_type != "caregiver":
        raise forbidden("Esta sección es solo para cuentas de cuidadora.")
    profile = (await db.execute(select(models.CaregiverProfile)
                                .where(models.CaregiverProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        profile = models.CaregiverProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


# ---------- 13.5 Mi perfil profesional ----------
@router.get("/profile", response_model=CaregiverProfileOut)
async def get_profile(db: Db, user: CurrentUser):
    return _out(await _get_own_profile(db, user))


# ---------- 13.6 Actualizar perfil profesional ----------
@router.put("/profile", response_model=CaregiverProfileOut)
async def update_profile(body: CaregiverProfilePatchIn, db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    if body.headline is not None:
        profile.headline = body.headline
    if body.bio is not None:
        profile.bio = body.bio
    if body.years_experience is not None:
        profile.years_experience = body.years_experience
    if body.specialties is not None:
        profile.specialties = body.specialties
    if body.languages is not None:
        profile.languages = body.languages
    if body.zones is not None:
        profile.zones = body.zones
    if body.certifications is not None:
        profile.certifications = [c.model_dump() for c in body.certifications]
    if body.is_listed is not None:
        profile.is_listed = body.is_listed
    await db.flush()
    await sync_caregiver_to_admin(profile, user, await _is_engaged(db, profile.id))
    return _out(profile)


# ---------- Documentos de respaldo (cédula, antecedentes, certificados) ----------
def _doc_out(d: models.CaregiverDocument) -> CaregiverDocumentOut:
    return CaregiverDocumentOut(doc_type=d.doc_type, file_url=d.file_url,
                                original_filename=d.original_filename, uploaded_at=d.uploaded_at,
                                status=d.status, pending_file_url=d.pending_file_url,
                                pending_filename=d.pending_filename, review_note=d.review_note,
                                reviewed_at=d.reviewed_at)


async def _reconcile_with_admin(user: models.User, docs: list[models.CaregiverDocument]) -> None:
    """Si el staff ya decidió en la Consola pero el aviso no llegó al sitio, toma su decisión.
    Solo adopta una decisión cuando se refiere al mismo archivo que la cuidadora tiene aquí."""
    from app.routers.internal import apply_review

    if not any(d.status != "approved" or d.pending_file_url for d in docs):
        return
    remote = {r["doc_type"]: r for r in await fetch_admin_documents(user.email)}
    for d in docs:
        a = remote.get(d.doc_type)
        if a is None or a.get("pending_file_url"):
            continue  # la Consola tiene otro cambio en espera: aún no hay decisión final
        if d.pending_file_url:
            if a["status"] == "approved" and a["file_url"] == d.pending_file_url:
                apply_review(d, "approve", a.get("review_note"))
        elif a["file_url"] == d.file_url and a["status"] in ("approved", "rejected") and a["status"] != d.status:
            apply_review(d, "approve" if a["status"] == "approved" else "reject", a.get("review_note"))


@router.get("/documents", response_model=list[CaregiverDocumentOut])
async def list_documents(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    rows = (await db.execute(select(models.CaregiverDocument)
                             .where(models.CaregiverDocument.caregiver_profile_id == profile.id)
                             )).scalars().all()
    await _reconcile_with_admin(user, rows)
    return [_doc_out(d) for d in rows]


@router.post("/documents", response_model=CaregiverDocumentOut, status_code=201)
async def upload_document(request: Request, db: Db, user: CurrentUser,
                          doc_type: CaregiverDocType = Form(...), file: UploadFile = File(...)):
    profile = await _get_own_profile(db, user)
    ext = DOCUMENT_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise ApiError(422, "INVALID_FILE_TYPE", "El documento debe ser PDF, JPG o PNG.")
    data = await file.read()
    if len(data) > storage.MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", f"El documento no puede superar los {storage.MAX_UPLOAD_LABEL}.")

    filename = f"{doc_type.value}-{int(now_utc().timestamp())}{ext}"
    file_url = await storage.save(f"documents/{profile.id}/{filename}", data, file.content_type,
                                  str(request.base_url))
    original_name = file.filename or filename

    existing = (await db.execute(select(models.CaregiverDocument).where(
        models.CaregiverDocument.caregiver_profile_id == profile.id,
        models.CaregiverDocument.doc_type == doc_type.value))).scalar_one_or_none()
    is_change = False
    if existing is None:
        existing = models.CaregiverDocument(caregiver_profile_id=profile.id, doc_type=doc_type.value,
                                            file_url=file_url, original_filename=original_name,
                                            status="pending")
        db.add(existing)
    elif existing.status == "approved":
        # El documento aprobado sigue vigente; el nuevo espera la aprobación del staff.
        is_change = True
        existing.pending_file_url = file_url
        existing.pending_filename = original_name
        existing.review_note = None
    else:
        existing.file_url = file_url
        existing.original_filename = original_name
        existing.status = "pending"
        existing.review_note = None
        existing.pending_file_url = None
        existing.pending_filename = None
    await db.flush()
    await db.refresh(existing)

    await sync_document_to_admin(user.email, doc_type.value, file_url, original_name, is_change)
    return _doc_out(existing)


# ---------- Mensajes de contacto recibidos ----------
@router.get("/contacts", response_model=Page[ContactMessageOut])
async def list_contacts(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    rows = (await db.execute(
        select(models.ContactRequest, models.User)
        .join(models.User, models.User.id == models.ContactRequest.family_user_id)
        .where(models.ContactRequest.caregiver_profile_id == profile.id)
        .order_by(models.ContactRequest.created_at.desc()))).all()
    items = [ContactMessageOut(contact_id=c.id, family_name=u.full_name, family_email=u.email,
                               message=c.message, created_at=c.created_at) for c, u in rows]
    return Page(items=items, total=len(items))


# ---------- Mis reseñas ----------
@router.get("/reviews", response_model=list[ReviewOut])
async def my_reviews(db: Db, user: CurrentUser):
    """Las reseñas que las familias le han dejado a la cuidadora (de la más nueva a la más antigua)."""
    profile = await _get_own_profile(db, user)
    rows = (await db.execute(select(models.CaregiverReview)
                             .where(models.CaregiverReview.caregiver_profile_id == profile.id)
                             .order_by(models.CaregiverReview.created_at.desc()))).scalars().all()
    return [ReviewOut(review_id=r.id, rating=r.rating, comment=r.comment, author_name=r.author_name,
                      created_at=r.created_at) for r in rows]


# ---------- Trabajo activo ----------
@router.get("/engagement", response_model=EngagementOut | None)
async def get_current_engagement(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    e = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == profile.id,
        models.CaregiverEngagement.status == "active")
        .order_by(models.CaregiverEngagement.started_at.desc()))).scalars().first()
    if e is None:
        return None
    return EngagementOut(engagement_id=e.id, family_name=e.family.full_name,
                         patient_name=e.patient.full_name if e.patient else None, started_at=e.started_at)


# ---------- Solicitudes de contratación ----------
def _received_out(r: models.HireRequest, family_name: str, conversation_id=None) -> ReceivedHireRequestOut:
    patient = r.patient
    age = None
    if patient is not None:
        today = date.today()
        b = patient.birth_date
        age = max(today.year - b.year - ((today.month, today.day) < (b.month, b.day)), 0)
    return ReceivedHireRequestOut(
        request_id=r.id, status=r.status, created_at=r.created_at, responded_at=r.responded_at,
        family_name=family_name, contact_name=r.family.full_name,
        patient_name=patient.full_name if patient else None, patient_age=age,
        conditions=(patient.conditions if patient else None) or [],
        medication_allergies=(patient.medication_allergies if patient else None) or [],
        food_allergies=(patient.food_allergies if patient else None) or [], message=r.message,
        conversation_id=conversation_id)


async def _family_label(db: Db, r: models.HireRequest) -> str:
    surname = (r.patient.full_name if r.patient else r.family.full_name).split()[-1]
    return f"Familia {surname}"


@router.get("/hire-requests", response_model=Page[ReceivedHireRequestOut])
async def list_hire_requests(db: Db, user: CurrentUser):
    """Solicitudes recibidas: las pendientes primero y, después, las respondidas en el último mes."""
    profile = await _get_own_profile(db, user)
    since = now_utc() - timedelta(days=30)
    rows = (await db.execute(select(models.HireRequest).where(
        models.HireRequest.caregiver_profile_id == profile.id,
        models.HireRequest.status != "cancelled",
        models.HireRequest.created_at >= since))).scalars().all()
    rows.sort(key=lambda r: (r.status != "pending", -r.created_at.timestamp()))
    convs = {c.family_user_id: c.id for c in (await db.execute(select(models.ChatConversation).where(
        models.ChatConversation.caregiver_profile_id == profile.id))).scalars().all()}
    return Page(items=[_received_out(r, await _family_label(db, r), convs.get(r.family_user_id)) for r in rows],
                total=len(rows))


async def _pending_request(db: Db, user: models.User, request_id: UUID):
    profile = await _get_own_profile(db, user)
    r = await db.get(models.HireRequest, request_id)
    if r is None or r.caregiver_profile_id != profile.id:
        raise not_found()
    if r.status != "pending":
        raise conflict("REQUEST_NOT_PENDING", "Esta solicitud ya no está pendiente.")
    return profile, r


@router.post("/hire-requests/{request_id}/accept", response_model=EngagementOut)
async def accept_hire_request(request_id: UUID, db: Db, user: CurrentUser):
    from app.routers.chat import add_message, get_or_create_conversation

    profile, r = await _pending_request(db, user, request_id)
    if await _is_engaged(db, profile.id):
        raise conflict("ALREADY_WORKING", "Ya tienes un trabajo activo. Termínalo antes de aceptar otro.")
    now = now_utc()
    engagement = models.CaregiverEngagement(caregiver_profile_id=profile.id, family_user_id=r.family_user_id,
                                            patient_id=r.patient_id)
    db.add(engagement)
    r.status = "accepted"
    r.responded_at = now
    # Las demás solicitudes pendientes quedan sin efecto: ya tiene un trabajo.
    others = (await db.execute(select(models.HireRequest).where(
        models.HireRequest.caregiver_profile_id == profile.id,
        models.HireRequest.status == "pending", models.HireRequest.id != r.id))).scalars().all()
    for o in others:
        o.status = "unavailable"
        o.responded_at = now
    await db.flush()
    await db.refresh(engagement)

    family_name = await _family_label(db, r)
    conv, _ = await get_or_create_conversation(db, profile, r.family)
    await add_message(db, conv, user, "¡Acepté tu solicitud de contratación! Coordinemos los detalles por aquí.")
    await sync_caregiver_to_admin(profile, user, True)
    return EngagementOut(engagement_id=engagement.id, family_name=family_name,
                         patient_name=r.patient.full_name if r.patient else None,
                         started_at=engagement.started_at or now)


@router.post("/hire-requests/{request_id}/decline", status_code=204)
async def decline_hire_request(request_id: UUID, db: Db, user: CurrentUser):
    from app.routers.chat import add_message, get_or_create_conversation

    profile, r = await _pending_request(db, user, request_id)
    r.status = "declined"
    r.responded_at = now_utc()
    conv, _ = await get_or_create_conversation(db, profile, r.family)
    await add_message(db, conv, user, "Gracias por tu solicitud. Por ahora no puedo aceptarla.")
