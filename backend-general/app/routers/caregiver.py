"""Perfil profesional de la cuidadora: base de su ficha en el marketplace."""
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from sqlalchemy import select

from app import models
from app.deps import CurrentUser, Db
from app.enums import CaregiverDocType
from app.errors import ApiError, forbidden
from app.schemas.common import Page
from app.schemas.marketplace import (CaregiverDocumentOut, CaregiverProfileOut,
                                     CaregiverProfilePatchIn, ContactMessageOut, EngagementOut)
from app.security import now_utc
from app.sync import sync_caregiver_to_admin, sync_document_to_admin

router = APIRouter(prefix="/caregiver", tags=["Perfil de cuidadora"])

DOCUMENT_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
DOCUMENT_MAX_BYTES = 8 * 1024 * 1024
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
                               is_featured=p.is_featured)


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
                                original_filename=d.original_filename, uploaded_at=d.uploaded_at)


@router.get("/documents", response_model=list[CaregiverDocumentOut])
async def list_documents(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    rows = (await db.execute(select(models.CaregiverDocument)
                             .where(models.CaregiverDocument.caregiver_profile_id == profile.id)
                             )).scalars().all()
    return [_doc_out(d) for d in rows]


@router.post("/documents", response_model=CaregiverDocumentOut, status_code=201)
async def upload_document(request: Request, db: Db, user: CurrentUser,
                          doc_type: CaregiverDocType = Form(...), file: UploadFile = File(...)):
    profile = await _get_own_profile(db, user)
    ext = DOCUMENT_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise ApiError(422, "INVALID_FILE_TYPE", "El documento debe ser PDF, JPG o PNG.")
    data = await file.read()
    if len(data) > DOCUMENT_MAX_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "El documento no puede superar los 8 MB.")

    doc_dir = DOCUMENT_DIR / str(profile.id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    for stale_ext in DOCUMENT_CONTENT_TYPES.values():
        (doc_dir / f"{doc_type.value}{stale_ext}").unlink(missing_ok=True)
    filename = f"{doc_type.value}{ext}"
    (doc_dir / filename).write_bytes(data)
    file_url = f"{str(request.base_url).rstrip('/')}/uploads/documents/{profile.id}/{filename}"

    existing = (await db.execute(select(models.CaregiverDocument).where(
        models.CaregiverDocument.caregiver_profile_id == profile.id,
        models.CaregiverDocument.doc_type == doc_type.value))).scalar_one_or_none()
    if existing is None:
        existing = models.CaregiverDocument(caregiver_profile_id=profile.id, doc_type=doc_type.value)
        db.add(existing)
    existing.file_url = file_url
    existing.original_filename = file.filename or filename
    await db.flush()

    await sync_document_to_admin(user.email, doc_type.value, file_url, existing.original_filename)
    return CaregiverDocumentOut(doc_type=existing.doc_type, file_url=existing.file_url,
                                original_filename=existing.original_filename,
                                uploaded_at=existing.uploaded_at or now_utc())


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
