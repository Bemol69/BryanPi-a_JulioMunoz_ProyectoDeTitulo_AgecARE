"""Modelos SQLAlchemy de la API general (usuarios, pacientes, marketplace).

Convenciones: PK UUID, timestamps con zona horaria, JSON portable.
Basado en la Especificación de Endpoints Backend v1, secciones 3, 4 y 14.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String,
                        Text, UniqueConstraint, Uuid, func)
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
    medication_allergies: Mapped[list] = mapped_column(PortableJSON, default=list)
    food_allergies: Mapped[list] = mapped_column(PortableJSON, default=list)
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
    # Estado de revisión que decide el staff en la Consola: solo las cuidadoras
    # 'approved' (y con is_listed) aparecen en el marketplace.
    admin_status: Mapped[str] = mapped_column(String(12), default="pending")  # pending | approved | suspended
    created_at: Mapped[datetime] = ts_now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    user: Mapped[User] = relationship(lazy="joined")


class CaregiverDocument(Base):
    """Documento de respaldo (cédula, certificado de antecedentes, certificados de
    cursos) que la cuidadora sube para optar a trabajos. Un documento por tipo:
    volver a subir el mismo tipo reemplaza el anterior."""
    __tablename__ = "caregiver_documents"
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(20))
    file_url: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    # Revisión del staff: pending (esperando) | approved | rejected. Si el documento ya está
    # aprobado y la cuidadora sube uno nuevo, el nuevo queda en pending_file_url hasta que el
    # staff lo apruebe (el aprobado sigue vigente mientras tanto).
    status: Mapped[str] = mapped_column(String(16), default="pending")
    pending_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pending_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                  onupdate=func.now())


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


class CaregiverEngagement(Base):
    """Un trabajo activo: una familia contrató a una cuidadora para un paciente.
    Mientras exista un registro con status='active' para una cuidadora, se
    sincroniza hacia la Consola como "actualmente trabajando"."""
    __tablename__ = "caregiver_engagements"
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    family_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active", index=True)  # active | ended
    started_at: Mapped[datetime] = ts_now()
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Reseña dejada por este trabajo: solo se puede reseñar un trabajo terminado, una vez.
    review_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    family: Mapped[User] = relationship(lazy="joined", foreign_keys=[family_user_id])
    patient: Mapped[Patient | None] = relationship(lazy="joined")


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


# ============ Chat dentro de la aplicación ============
class ChatConversation(Base):
    """Conversación entre una familia y una cuidadora. Los mensajes se eliminan solos a los
    7 días (ver app/chat_retention.py)."""
    __tablename__ = "chat_conversations"
    __table_args__ = (UniqueConstraint("caregiver_profile_id", "family_user_id", name="uq_chat_pair"),)
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    family_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = ts_now()
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    family: Mapped[User] = relationship(lazy="joined", foreign_keys=[family_user_id])
    caregiver: Mapped[CaregiverProfile] = relationship(lazy="joined")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[uuid.UUID] = pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_conversations.id"), index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class HireRequest(Base):
    """Solicitud de contratación: la familia la envía y la cuidadora la acepta o la rechaza.
    Al aceptarla se crea el trabajo activo (CaregiverEngagement)."""
    __tablename__ = "hire_requests"
    id: Mapped[uuid.UUID] = pk()
    caregiver_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_profiles.id"), index=True)
    family_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # pending | accepted | declined | cancelled | unavailable (la cuidadora aceptó otro trabajo antes)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    created_at: Mapped[datetime] = ts_now()
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    family: Mapped[User] = relationship(lazy="joined", foreign_keys=[family_user_id])
    patient: Mapped[Patient | None] = relationship(lazy="joined")
