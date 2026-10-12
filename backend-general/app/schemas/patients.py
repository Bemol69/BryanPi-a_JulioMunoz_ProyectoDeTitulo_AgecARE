"""Esquemas de pacientes (Especificación Backend v1, sección 4)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import Sex


class PatientCreateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    birth_date: date
    sex: Sex | None = None
    photo_url: str | None = Field(default=None, max_length=500)
    conditions: list[str] = Field(default_factory=list)
    medication_allergies: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class PatientCreateOut(BaseModel):
    patient_id: UUID
    full_name: str
    created_at: datetime


class PatientCardOut(BaseModel):
    patient_id: UUID
    full_name: str
    photo_url: str | None
    role: str
    wellbeing_status: str = "ok"  # placeholder: el módulo de salud no está en este alcance


class PatientOut(BaseModel):
    patient_id: UUID
    full_name: str
    birth_date: date
    sex: Sex | None
    photo_url: str | None
    conditions: list[str]
    medication_allergies: list[str]
    food_allergies: list[str]
    notes: str | None


class PatientCaregiverOut(BaseModel):
    engagement_id: UUID
    profile_id: UUID
    full_name: str
    photo_url: str | None
    started_at: datetime


class PatientDetailOut(PatientOut):
    """Ficha del adulto mayor con su estado actual de cuidado."""
    age: int
    caregiver: PatientCaregiverOut | None = None  # cuidadora con trabajo activo, si la hay
    wellbeing_status: str = "ok"  # placeholder: el módulo de salud no está en este alcance
