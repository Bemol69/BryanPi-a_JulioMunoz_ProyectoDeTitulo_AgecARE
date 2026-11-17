"""Reglas de contratación: cada adulto mayor tiene como máximo UNA cuidadora activa a la vez.
Una familia con dos adultos mayores puede tener dos cuidadoras (una por cada uno). Los trabajos
terminados quedan en el historial y no cuentan."""
from sqlalchemy import select

from app import models


async def patient_engagement(db, patient_id) -> models.CaregiverEngagement | None:
    """Trabajo activo de ese adulto mayor, lo haya contratado quien lo haya contratado."""
    return (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.patient_id == patient_id,
        models.CaregiverEngagement.status == "active").limit(1))).scalars().first()


async def engagement_blocking(db, family_user_id, patient_id) -> models.CaregiverEngagement | None:
    """Trabajo activo que impide contratar a otra cuidadora para ese adulto mayor. Sin adulto mayor
    (cuentas antiguas) se cuenta el trabajo sin adulto mayor de la propia cuenta."""
    if patient_id is not None:
        return await patient_engagement(db, patient_id)
    return (await db.execute(select(models.CaregiverEngagement).where(
        models.CaregiverEngagement.family_user_id == family_user_id,
        models.CaregiverEngagement.patient_id.is_(None),
        models.CaregiverEngagement.status == "active").limit(1))).scalars().first()


async def resolve_patient(db, user, requested):
    """Adulto mayor al que se dirige la solicitud y, si ya tiene cuidadora, el trabajo que lo impide.

    Si la familia no eligió uno se toma el primero que aún no tiene cuidadora; si todos la tienen
    devuelve el primero con su trabajo (la solicitud se rechaza)."""
    if requested is not None:
        return requested, await patient_engagement(db, requested)
    ids = list((await db.execute(select(models.PatientMember.patient_id).where(
        models.PatientMember.user_id == user.id).order_by(models.PatientMember.id))).scalars().all())
    if not ids:
        return None, await engagement_blocking(db, user.id, None)
    first_busy = None
    for pid in ids:
        current = await patient_engagement(db, pid)
        if current is None:
            return pid, None
        first_busy = first_busy or (pid, current)
    return first_busy


async def caregiver_name(db, caregiver_profile_id) -> str:
    profile = await db.get(models.CaregiverProfile, caregiver_profile_id)
    return profile.user.full_name if profile is not None else "otra cuidadora"


async def patient_first_name(db, patient_id) -> str | None:
    patient = await db.get(models.Patient, patient_id) if patient_id is not None else None
    return patient.full_name.split()[0] if patient is not None else None
