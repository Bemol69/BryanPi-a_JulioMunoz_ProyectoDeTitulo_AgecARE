"""Modelos SQLAlchemy de la API general (usuarios, pacientes, marketplace).

Convenciones: PK UUID, timestamps con zona horaria, JSON portable.
Basado en la Especificación de Endpoints Backend v1, secciones 3, 4 y 14.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String,
                        Text, Uuid, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PortableJSON = JSON().with_variant(JSONB(), "postgresql")


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def ts_now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ============ Cuentas ============
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locale: Mapped[str] = mapped_column(String(5), default="es")
    account_type: Mapped[str] = mapped_column(String(12))  # family | caregiver
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = ts_now()


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = ts_now()


# ============ Pacientes y círculo de cuidado (sección 4) ============
class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[uuid.UUID] = pk()
    full_name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    conditions: Mapped[list] = mapped_column(PortableJSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts_now()


class PatientMember(Base):
    """Membresía: quién tiene acceso a qué paciente y con qué rol (sección 4)."""
    __tablename__ = "patient_members"
    id: Mapped[uuid.UUID] = pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # enum RoleType
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = ts_now()

    patient: Mapped[Patient] = relationship(lazy="joined")


# ============ Marketplace (sección 13.5/13.6 y 14) ============
class CaregiverProfile(Base):
    __tablename__ = "caregiver_profiles"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    headline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    specialties: Mapped[list] = mapped_column(PortableJSON, default=list)
    languages: Mapped[list] = mapped_column(PortableJSON, default=list)
    zones: Mapped[list] = mapped_column(PortableJSON, default=list)
    certifications: Mapped[list] = mapped_column(PortableJSON, default=list)  # [{name, issuer, year}]
    rating_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = ts_now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    user: Mapped[User] = relationship(lazy="joined")


class CaregiverReview(Base):
    __tablename__ = "caregiver_reviews"
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    author_name: Mapped[str] = mapped_column(String(120))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts_now()


class ContactRequest(Base):
    __tablename__ = "contact_requests"
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    family_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = ts_now()


class MarketProduct(Base):
    __tablename__ = "market_products"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(20), index=True)
    description: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photos: Mapped[list] = mapped_column(PortableJSON, default=list)
    price_range: Mapped[str] = mapped_column(String(60))
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
