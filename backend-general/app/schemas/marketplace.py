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


class ReviewOut(BaseModel):
    review_id: UUID
    rating: int
    comment: str | None
    author_name: str
    created_at: datetime


class CaregiverPublicOut(CaregiverProfileOut):
    full_name: str
    photo_url: str | None
    reviews: list[ReviewOut] = []


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


class ReviewCreateIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


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
