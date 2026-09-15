"""Enumeraciones de dominio."""
from enum import StrEnum


class RoleType(StrEnum):
    family = "family"
    caregiver = "caregiver"
    doctor = "doctor"
    elder = "elder"


class AccountType(StrEnum):
    family = "family"
    caregiver = "caregiver"


class Sex(StrEnum):
    female = "female"
    male = "male"
    other = "other"


class ProductCategory(StrEnum):
    mobility = "mobility"
    monitoring = "monitoring"
    home_safety = "home_safety"
    daily_care = "daily_care"


class ContactChannel(StrEnum):
    phone = "phone"
    whatsapp = "whatsapp"
    email = "email"
