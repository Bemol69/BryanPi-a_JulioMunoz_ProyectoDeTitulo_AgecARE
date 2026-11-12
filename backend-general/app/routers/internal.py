"""Endpoints servidor-a-servidor: los llama la Consola de Administración (con la clave
compartida X-Internal-Key) cuando el staff aprueba, suspende o revisa documentos."""
from datetime import datetime, timedelta
from uuid import UUID
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app import accounts, models, storage
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


class ReviewModerationIn(BaseModel):
    email: str
    action: Literal["archive", "restore", "delete"]
    review_id: UUID | None = None  # si falta (reseñas antiguas), se busca por autor, nota y comentario
    family_name: str | None = None
    rating: int | None = None
    comment: str | None = None


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


@router.delete("/caregivers", status_code=204)
async def delete_caregiver_account(db: Db, email: str = Query(max_length=254)):
    """La Consola elimina el perfil de una cuidadora: se borra su cuenta del sitio con todos sus datos."""
    user = (await db.execute(select(models.User).where(func.lower(models.User.email) == email.lower(),
                                                      models.User.account_type == "caregiver"))).scalars().first()
    if user is None:
        raise not_found("No existe una cuidadora con ese correo.")
    paths = await accounts.purge_user(db, user, force=True)
    await db.flush()
    await storage.delete(paths)


@router.post("/reviews/moderate", status_code=204)
async def moderate_review(body: ReviewModerationIn, db: Db):
    """El staff archivó, restauró o eliminó una reseña en la Consola: aquí se oculta/muestra/borra
    y se recalcula la nota de la cuidadora."""
    p = await _profile_by_email(db, body.email)
    stmt = select(models.CaregiverReview).where(models.CaregiverReview.caregiver_profile_id == p.id)
    if body.review_id is not None:
        stmt = stmt.where(models.CaregiverReview.id == body.review_id)
    else:
        stmt = stmt.where(models.CaregiverReview.author_name == body.family_name,
                          models.CaregiverReview.rating == body.rating,
                          models.CaregiverReview.comment == body.comment)
    review = (await db.execute(stmt.order_by(models.CaregiverReview.created_at.desc()))).scalars().first()
    if review is None:
        return  # ya no existe en el sitio: nada que hacer
    if body.action == "delete":
        await db.delete(review)
    else:
        review.hidden = body.action == "archive"
    await db.flush()
    await accounts.recalc_ratings(db, {p.id})


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


# ---------- Catálogo de artículos de apoyo (lo administra la Consola) ----------
class ProductUpsertIn(BaseModel):
    id: UUID  # el mismo id que tiene el producto en la Consola
    name: str = Field(max_length=160)
    category: Literal["mobility", "monitoring", "home_safety", "daily_care"]
    vendor: str = Field(default="", max_length=120)
    description: str = ""
    price_clp: int | None = Field(default=None, ge=0)
    external_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    is_sponsored: bool = False
    conditions: list[str] = Field(default_factory=list)
    is_active: bool = True


@router.post("/products", status_code=204)
async def upsert_product(body: ProductUpsertIn, db: Db):
    """Crea o actualiza un producto con el mismo id de la Consola. `is_active=false` lo oculta del sitio."""
    from app.routers.marketplace import format_clp  # evita importar el router completo al cargar este módulo
    p = await db.get(models.MarketProduct, body.id)
    if p is None:
        p = models.MarketProduct(id=body.id, photos=[])
        db.add(p)
    p.name = body.name
    p.category = body.category
    p.vendor = body.vendor
    p.description = body.description
    p.price_clp = body.price_clp
    p.price_range = format_clp(body.price_clp)
    p.external_url = body.external_url
    p.thumbnail_url = body.image_url
    p.is_sponsored = body.is_sponsored
    p.conditions = body.conditions
    p.is_active = body.is_active


@router.get("/products/stats")
async def product_stats(db: Db):
    """Clics en "Ver en tienda" por producto (total y últimos 30 días), para el panel de la Consola."""
    since = now_utc() - timedelta(days=30)
    rows = (await db.execute(
        select(models.ProductClick.product_id, func.count(models.ProductClick.id),
               func.count(models.ProductClick.id).filter(models.ProductClick.created_at >= since))
        .group_by(models.ProductClick.product_id))).all()
    return {"items": [{"product_id": str(pid), "clicks_total": int(total), "clicks_30d": int(recent)}
                      for pid, total, recent in rows]}
