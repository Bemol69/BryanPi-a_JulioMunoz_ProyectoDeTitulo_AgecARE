"""Endpoints servidor-a-servidor: los llama la Consola de Administración (con la clave
compartida X-Internal-Key) cuando el staff aprueba, suspende o revisa documentos."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app import models
from app.deps import Db, require_internal_key
from app.errors import not_found
from app.security import now_utc

router = APIRouter(prefix="/internal", tags=["Interno (Consola)"],
                   dependencies=[Depends(require_internal_key)])


class StatusIn(BaseModel):
    email: str
    status: Literal["pending", "approved", "suspended"]


class DocumentReviewIn(BaseModel):
    email: str
    doc_type: str
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class InternalDocumentOut(BaseModel):
    doc_type: str
    file_url: str
    original_filename: str
    status: str
    pending_file_url: str | None
    pending_filename: str | None
    uploaded_at: datetime


async def _profile_by_email(db: Db, email: str) -> models.CaregiverProfile:
    p = (await db.execute(select(models.CaregiverProfile)
                          .join(models.User, models.User.id == models.CaregiverProfile.user_id)
                          .where(func.lower(models.User.email) == email.lower()))).scalars().first()
    if p is None:
        raise not_found("No existe una cuidadora con ese correo.")
    return p


def apply_review(d: models.CaregiverDocument, action: str, note: str | None) -> None:
    """Aplica la decisión del staff (misma lógica que usa la Consola en su propia copia)."""
    d.reviewed_at = now_utc()
    d.review_note = note
    if action == "approve":
        if d.pending_file_url:  # el cambio propuesto pasa a ser el documento vigente
            d.file_url = d.pending_file_url
            d.original_filename = d.pending_filename or d.original_filename
            d.pending_file_url = None
            d.pending_filename = None
        d.status = "approved"
    elif d.pending_file_url:  # se descarta el cambio; el documento aprobado sigue vigente
        d.pending_file_url = None
        d.pending_filename = None
        d.status = "approved"
    else:
        d.status = "rejected"


@router.post("/caregivers/status", status_code=204)
async def set_caregiver_status(body: StatusIn, db: Db):
    """Estado de revisión del perfil: solo 'approved' permite aparecer en el marketplace."""
    (await _profile_by_email(db, body.email)).admin_status = body.status


@router.post("/documents/review", status_code=204)
async def review_document(body: DocumentReviewIn, db: Db):
    p = await _profile_by_email(db, body.email)
    d = (await db.execute(select(models.CaregiverDocument).where(
        models.CaregiverDocument.caregiver_profile_id == p.id,
        models.CaregiverDocument.doc_type == body.doc_type))).scalars().first()
    if d is None:
        raise not_found("La cuidadora no ha subido ese documento.")
    apply_review(d, body.action, body.note)


@router.get("/caregivers/documents", response_model=list[InternalDocumentOut])
async def caregiver_documents(db: Db, email: str = Query(max_length=254)):
    """La Consola consulta aquí los documentos de una cuidadora, por si la notificación de
    subida no llegó (instancia dormida, error de red)."""
    p = await _profile_by_email(db, email)
    rows = (await db.execute(select(models.CaregiverDocument)
                             .where(models.CaregiverDocument.caregiver_profile_id == p.id))).scalars().all()
    return [InternalDocumentOut(doc_type=d.doc_type, file_url=d.file_url,
                                original_filename=d.original_filename, status=d.status,
                                pending_file_url=d.pending_file_url, pending_filename=d.pending_filename,
                                uploaded_at=d.uploaded_at or now_utc()) for d in rows]
