"""Esquemas de autenticación (Especificación Backend v1, sección 3)."""
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.enums import AccountType, RoleType


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)
    account_type: AccountType
    locale: str = "es"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MembershipOut(BaseModel):
    patient_id: UUID
    patient_name: str
    role: RoleType


class UserOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    phone: str | None
    avatar_url: str | None
    locale: str
    account_type: AccountType
    memberships: list[MembershipOut] = []

    model_config = {"from_attributes": True}


class AuthOut(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(BaseModel):
    access_token: str
    refresh_token: str


class UserPatchIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=500)
    locale: str | None = None
