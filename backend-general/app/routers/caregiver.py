"""Perfil profesional de la cuidadora: base de su ficha en el marketplace."""
from fastapi import APIRouter
from sqlalchemy import select

from app import models
from app.deps import CurrentUser, Db
from app.errors import forbidden
from app.schemas.common import Page
from app.schemas.marketplace import CaregiverProfileOut, CaregiverProfilePatchIn, ContactMessageOut, EngagementOut
from app.sync import sync_caregiver_to_admin

router = APIRouter(prefix="/caregiver", tags=["Perfil de cuidadora"])


async def _is_engaged(db: Db, caregiver_profile_id) -> bool:
    active = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == caregiver_profile_id,
        models.CaregiverEngagement.status == "active"))).first()
    return active is not None


def _out(p: models.CaregiverProfile) -> CaregiverProfileOut:
    return CaregiverProfileOut(profile_id=p.id, headline=p.headline, bio=p.bio,
                               years_experience=p.years_experience, specialties=p.specialties or [],
                               languages=p.languages or [], zones=p.zones or [],
                               certifications=p.certifications or [], rating_avg=p.rating_avg,
                               reviews_count=p.reviews_count, is_listed=p.is_listed,
                               is_featured=p.is_featured)


async def _get_own_profile(db: Db, user: models.User) -> models.CaregiverProfile:
    if user.account_type != "caregiver":
        raise forbidden("Esta sección es solo para cuentas de cuidadora.")
    profile = (await db.execute(select(models.CaregiverProfile)
                                .where(models.CaregiverProfile.user_id == user.id))).scalar_one_or_none()
    if profile is None:
        profile = models.CaregiverProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


# ---------- 13.5 Mi perfil profesional ----------
@router.get("/profile", response_model=CaregiverProfileOut)
async def get_profile(db: Db, user: CurrentUser):
    return _out(await _get_own_profile(db, user))


# ---------- 13.6 Actualizar perfil profesional ----------
@router.put("/profile", response_model=CaregiverProfileOut)
async def update_profile(body: CaregiverProfilePatchIn, db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    if body.headline is not None:
        profile.headline = body.headline
    if body.bio is not None:
        profile.bio = body.bio
    if body.years_experience is not None:
        profile.years_experience = body.years_experience
    if body.specialties is not None:
        profile.specialties = body.specialties
    if body.languages is not None:
        profile.languages = body.languages
    if body.zones is not None:
        profile.zones = body.zones
    if body.certifications is not None:
        profile.certifications = [c.model_dump() for c in body.certifications]
    if body.is_listed is not None:
        profile.is_listed = body.is_listed
    await db.flush()
    await sync_caregiver_to_admin(profile, user, await _is_engaged(db, profile.id))
    return _out(profile)


# ---------- Mensajes de contacto recibidos ----------
@router.get("/contacts", response_model=Page[ContactMessageOut])
async def list_contacts(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    rows = (await db.execute(
        select(models.ContactRequest, models.User)
        .join(models.User, models.User.id == models.ContactRequest.family_user_id)
        .where(models.ContactRequest.caregiver_profile_id == profile.id)
        .order_by(models.ContactRequest.created_at.desc()))).all()
    items = [ContactMessageOut(contact_id=c.id, family_name=u.full_name, family_email=u.email,
                               message=c.message, created_at=c.created_at) for c, u in rows]
    return Page(items=items, total=len(items))


# ---------- Trabajo activo ----------
@router.get("/engagement", response_model=EngagementOut | None)
async def get_current_engagement(db: Db, user: CurrentUser):
    profile = await _get_own_profile(db, user)
    e = (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.caregiver_profile_id == profile.id,
        models.CaregiverEngagement.status == "active")
        .order_by(models.CaregiverEngagement.started_at.desc()))).scalars().first()
    if e is None:
        return None
    return EngagementOut(engagement_id=e.id, family_name=e.family.full_name,
                         patient_name=e.patient.full_name if e.patient else None, started_at=e.started_at)
