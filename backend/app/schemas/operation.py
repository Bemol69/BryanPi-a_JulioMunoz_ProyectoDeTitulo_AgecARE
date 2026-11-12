"""Esquemas de contenido, marketplace y moderación."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.enums import (CaregiverStatus, ContentStatus, ContentType, ModerationItemType,
                       ModerationStatus, RejectReason)


# ---- Contenido ----
class ContentItemOut(BaseModel):
    id: UUID
    type: ContentType
    title: str
    body: str
    audio_available: bool
    tags: list[str]
    status: ContentStatus
    publish_at: datetime | None
    published_at: datetime | None
    created_by_name: str | None
    updated_at: datetime


class ContentCreateIn(BaseModel):
    type: ContentType
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=10, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    publish_at: datetime | None = None


class ContentPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    body: str | None = Field(default=None, min_length=10, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=10)
    publish_at: datetime | None = None


# ---- Marketplace ----
class CaregiverDocumentOut(BaseModel):
    doc_type: str
    file_url: str
    original_filename: str
    uploaded_at: datetime
    status: str = "pending"  # pending | approved | rejected
    pending_file_url: str | None = None  # cambio propuesto, esperando decisión del staff
    pending_filename: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by_name: str | None = None


class CaregiverDocumentSyncIn(BaseModel):
    """Documento reenviado por el sitio público cuando una cuidadora lo sube."""
    caregiver_email: str
    doc_type: str
    file_url: str
    original_filename: str = Field(max_length=255)
    is_change: bool = False  # reemplaza a un documento ya aprobado


class CaregiverDocumentReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class CaregiverStatusItem(BaseModel):
    email: str
    status: CaregiverStatus


class CaregiverOut(BaseModel):
    caregiver_id: UUID
    name: str
    photo_url: str | None = None
    zone: str
    specialties: list[str]
    languages: list[str]
    certifications_count: int
    rating_avg: float | None
    reviews_count: int
    is_engaged: bool
    status: CaregiverStatus
    submitted_at: datetime
    reviewed_by_name: str | None
    internal_note: str | None = None
    certifications_verified: bool = False  # cédula y antecedentes aprobados: permite aprobar el perfil
    pending_documents: int = 0  # documentos (o cambios) esperando revisión
    documents: list[CaregiverDocumentOut] = []
    verification_fee_status: Literal["unpaid", "paid", "waived"] = "waived"
    verification_fee_clp: int = 0
    verification_reference: str | None = None
    verification_paid_at: datetime | None = None
    verification_marked_by: str | None = None


class VerificationIn(BaseModel):
    """Decisión del equipo sobre el cobro de verificación de una cuidadora."""
    action: Literal["paid", "waived", "unpaid"]


class VerificationSiteOut(BaseModel):
    """Lo que el sitio público muestra a la cuidadora sobre su pago."""
    fee_clp: int
    status: Literal["unpaid", "paid", "waived"]
    reference: str | None = None
    paid_at: datetime | None = None


class CaregiverPatchIn(BaseModel):
    status: CaregiverStatus | None = None
    reason: str | None = Field(default=None, min_length=10, max_length=1000)
    internal_note: str | None = Field(default=None, max_length=2000)


class CaregiverSyncIn(BaseModel):
    """Datos enviados por el sitio público cuando una cuidadora publica su perfil."""
    external_user_id: str
    name: str = Field(min_length=2, max_length=120)
    email: str
    zone: str = Field(max_length=80)
    specialties: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications_count: int = 0
    is_engaged: bool = False
    photo_url: str | None = Field(default=None, max_length=500)


class CaregiverReviewIn(BaseModel):
    caregiver_id: UUID
    family_name: str = Field(min_length=2, max_length=120)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    job_reference: str | None = Field(default=None, max_length=120)


class CaregiverReviewSyncIn(BaseModel):
    """Reseña reenviada por el sitio público cuando una familia reseña a una cuidadora."""
    caregiver_email: str
    family_name: str = Field(min_length=2, max_length=120)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    review_id: UUID | None = None  # id de la reseña en el sitio público


class CaregiverReviewOut(BaseModel):
    id: UUID
    caregiver_id: UUID
    family_name: str
    rating: int
    comment: str | None
    job_reference: str | None
    points_awarded: int
    created_at: datetime
    archived_at: datetime | None = None
    archived_by_name: str | None = None


class ReviewArchiveIn(BaseModel):
    archived: bool


class CaregiverPointsIn(BaseModel):
    points: int = Field(gt=0, le=1000)
    reason: str = Field(pattern="^(job_completed|good_review|manual)$")
    note: str | None = Field(default=None, max_length=300)


class CaregiverPointsOut(BaseModel):
    caregiver_id: UUID
    points_awarded: int
    reason: str
    total_points: int
    created_at: datetime


class CaregiverRankingItem(BaseModel):
    rank: int
    caregiver_id: UUID
    name: str
    photo_url: str | None = None
    zone: str
    points: int
    rating_avg: float | None
    reviews_count: int
    status: CaregiverStatus


ProductCategoryKey = Literal["mobility", "monitoring", "home_safety", "daily_care"]


class ProductOut(BaseModel):
    id: UUID
    name: str
    category: str
    vendor: str
    price_clp: int | None
    external_url: str
    image_url: str | None
    status: ContentStatus
    updated_at: datetime
    description: str | None = None
    is_sponsored: bool = False
    conditions: list[str] = []
    commission_pct: float | None = None
    # Clics en "Ver en tienda" según el sitio público (None si no respondió).
    clicks_total: int | None = None
    clicks_30d: int | None = None

    model_config = {"from_attributes": True}

    @field_validator("conditions", mode="before")
    @classmethod
    def _conditions_not_null(cls, v):
        return v or []


def _https(v: HttpUrl | None) -> HttpUrl | None:
    if v is not None and v.scheme != "https":
        raise ValueError("El enlace debe usar https.")
    return v


class ProductCreateIn(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    category: ProductCategoryKey
    vendor: str = Field(min_length=2, max_length=120)
    price_clp: int | None = Field(default=None, ge=0)
    external_url: HttpUrl
    image_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=1000)
    is_sponsored: bool = False
    conditions: list[str] = Field(default_factory=list, max_length=12)
    commission_pct: float | None = Field(default=None, ge=0, le=100)
    status: ContentStatus = ContentStatus.published


    @field_validator("external_url", "image_url")
    @classmethod
    def https_only(cls, v: HttpUrl | None) -> HttpUrl | None:
        return _https(v)


class ProductPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=160)
    category: ProductCategoryKey | None = None
    vendor: str | None = Field(default=None, min_length=2, max_length=120)
    price_clp: int | None = Field(default=None, ge=0)
    external_url: HttpUrl | None = None
    image_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=1000)
    is_sponsored: bool | None = None
    conditions: list[str] | None = Field(default=None, max_length=12)
    commission_pct: float | None = Field(default=None, ge=0, le=100)
    status: ContentStatus | None = None


    @field_validator("external_url", "image_url")
    @classmethod
    def https_only(cls, v: HttpUrl | None) -> HttpUrl | None:
        return _https(v)


class MonetizationOut(BaseModel):
    """Resumen de ingresos del marketplace para la Consola."""
    verification_fee_clp: int  # tarifa vigente
    verification_paid_count: int
    verification_paid_total_clp: int
    verification_pending_count: int
    verification_pending_total_clp: int
    verification_waived_count: int
    products_published: int
    products_sponsored: int
    clicks_30d: int | None  # None si el sitio público no respondió
    clicks_total: int | None
    # Estimación = clics 30 días × conversión supuesta × precio × comisión pactada de cada producto.
    estimated_commission_30d_clp: int | None
    assumed_conversion_pct: float


# ---- Moderación ----
class ModerationItemOut(BaseModel):
    id: UUID
    type: ModerationItemType
    content: dict
    author: dict
    reported_by: dict | None
    report_reason: str | None
    status: ModerationStatus
    decided_by_name: str | None
    decided_at: datetime | None
    created_at: datetime


class ApproveIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class RejectIn(BaseModel):
    reason_code: RejectReason
    note: str | None = Field(default=None, max_length=1000)
