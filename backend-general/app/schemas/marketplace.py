"""Esquemas de marketplace y perfil profesional (Especificación Backend v1,
secciones 13.5/13.6 y 14)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import ContactChannel, ProductCategory


class CertificationIn(BaseModel):
    name: str = Field(max_length=160)
    issuer: str | None = Field(default=None, max_length=160)
    year: int | None = None


class CaregiverProfilePatchIn(BaseModel):
    headline: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    specialties: list[str] | None = None
    languages: list[str] | None = None
    zones: list[str] | None = None
    certifications: list[CertificationIn] | None = None
    is_listed: bool | None = None


class CaregiverDocumentOut(BaseModel):
    doc_type: str
    file_url: str
    original_filename: str
    uploaded_at: datetime
    status: str = "pending"  # pending | approved | rejected
    pending_file_url: str | None = None  # cambio propuesto, esperando aprobación del staff
    pending_filename: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None


class CaregiverProfileOut(BaseModel):
    profile_id: UUID
    headline: str | None
    bio: str | None
    years_experience: int | None
    specialties: list[str]
    languages: list[str]
    zones: list[str]
    certifications: list[dict]
    rating_avg: float | None
    reviews_count: int
    is_listed: bool
    is_featured: bool
    admin_status: str = "pending"  # pending | approved | suspended (lo decide el staff)


# ---- Marketplace público (familia) ----
class CaregiverCardOut(BaseModel):
    profile_id: UUID
    full_name: str
    photo_url: str | None
    headline: str | None
    years_experience: int | None
    specialties: list[str]
    zones: list[str]
    rating_avg: float | None
    reviews_count: int
    is_featured: bool
    is_engaged: bool = False  # tiene un trabajo activo con alguna familia


class ReviewOut(BaseModel):
    review_id: UUID
    rating: int
    comment: str | None
    author_name: str
    created_at: datetime


class MyHireRequestOut(BaseModel):
    """Mi última solicitud a esta cuidadora (la familia ve su estado en el perfil)."""
    request_id: UUID
    status: str  # pending | declined | unavailable
    created_at: datetime


class CaregiverPublicOut(CaregiverProfileOut):
    full_name: str
    photo_url: str | None
    reviews: list[ReviewOut] = []
    hired_by_me: bool = False
    my_engagement_id: UUID | None = None
    is_engaged: bool = False
    can_review: bool = False  # la familia terminó un trabajo con ella y aún no lo reseñó
    conversation_id: UUID | None = None
    my_request: MyHireRequestOut | None = None


class HireRequestIn(BaseModel):
    patient_id: UUID | None = None
    message: str | None = Field(default=None, max_length=500)


class HireRequestOut(BaseModel):
    request_id: UUID
    status: str
    created_at: datetime
    conversation_id: UUID | None = None  # el chat donde se conversa la solicitud


class ReceivedHireRequestOut(BaseModel):
    """Solicitud que ve la cuidadora: quién la envía y a quién habría que cuidar."""
    request_id: UUID
    status: str  # pending | accepted | declined | cancelled | unavailable
    created_at: datetime
    responded_at: datetime | None
    family_name: str  # "Familia <apellido>"
    contact_name: str  # persona que envió la solicitud
    patient_name: str | None
    patient_age: int | None
    conditions: list[str]
    medication_allergies: list[str]
    food_allergies: list[str]
    message: str | None
    conversation_id: UUID | None = None  # chat con la familia


class EngagementOut(BaseModel):
    engagement_id: UUID
    family_name: str
    patient_name: str | None
    started_at: datetime


class ContactMessageOut(BaseModel):
    contact_id: UUID
    family_name: str
    family_email: str
    message: str | None
    created_at: datetime


class ContactIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class ContactOut(BaseModel):
    contact_channel: ContactChannel
    contact_value: str
    conversation_id: UUID | None = None


class ReviewCreateIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    patient_id: UUID | None = None


class ReviewCreateOut(BaseModel):
    review_id: UUID


# ---- Catálogo de artículos ----
class ProductCardOut(BaseModel):
    product_id: UUID
    name: str
    category: ProductCategory
    thumbnail_url: str | None
    price_range: str


class ProductOut(BaseModel):
    product_id: UUID
    name: str
    category: ProductCategory
    description: str
    photos: list[str]
    price_range: str
    external_url: str | None
    contact_info: str | None
