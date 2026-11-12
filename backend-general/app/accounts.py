"""Eliminación de familiares y de cuentas, con todos los datos que cuelgan de ellos.

Se usa desde el sitio (la persona elimina a un familiar o su propia cuenta) y desde la Consola
(el equipo elimina el perfil de una cuidadora). Devuelve las rutas de los archivos subidos para que
quien llama las borre del almacenamiento una vez hecho el cambio en la base de datos."""
from uuid import UUID

from sqlalchemy import delete, func, select, update

from app import models, storage
from app.errors import conflict


async def _has_active_engagement(db, *, family_user_id: UUID | None = None,
                                 caregiver_profile_id: UUID | None = None,
                                 patient_id: UUID | None = None) -> bool:
    cond = [models.CaregiverEngagement.status == "active"]
    if family_user_id is not None:
        cond.append(models.CaregiverEngagement.family_user_id == family_user_id)
    if caregiver_profile_id is not None:
        cond.append(models.CaregiverEngagement.caregiver_profile_id == caregiver_profile_id)
    if patient_id is not None:
        cond.append(models.CaregiverEngagement.patient_id == patient_id)
    return (await db.execute(select(models.CaregiverEngagement.id).where(*cond).limit(1))).first() is not None


async def recalc_ratings(db, profile_ids: set[UUID]) -> None:
    """Recalcula la valoración de las cuidadoras (las reseñas archivadas no cuentan)."""
    for pid in profile_ids:
        profile = await db.get(models.CaregiverProfile, pid)
        if profile is None:
            continue
        n, avg = (await db.execute(select(func.count(models.CaregiverReview.id),
                                          func.avg(models.CaregiverReview.rating))
                                   .where(models.CaregiverReview.caregiver_profile_id == pid,
                                          models.CaregiverReview.hidden.is_(False)))).one()
        profile.reviews_count = int(n or 0)
        profile.rating_avg = round(float(avg), 2) if n else None


async def purge_patient(db, patient: models.Patient) -> list[str]:
    """Elimina a un familiar. Si tiene una cuidadora trabajando, primero hay que cerrar ese trabajo."""
    if await _has_active_engagement(db, patient_id=patient.id):
        raise conflict("ACTIVE_ENGAGEMENT",
                       "Este familiar tiene una cuidadora trabajando. Cierra el trabajo antes de eliminarlo.")
    paths = [storage.path_from_url(patient.photo_url)]
    await db.execute(delete(models.HireRequest).where(models.HireRequest.patient_id == patient.id))
    # El historial de trabajos terminados se conserva (con las reseñas), sin el vínculo al familiar.
    await db.execute(update(models.CaregiverEngagement)
                     .where(models.CaregiverEngagement.patient_id == patient.id).values(patient_id=None))
    await db.execute(delete(models.PatientMember).where(models.PatientMember.patient_id == patient.id))
    await db.execute(delete(models.Patient).where(models.Patient.id == patient.id))
    return [p for p in paths if p]


async def purge_user(db, user: models.User, *, force: bool = False) -> list[str]:
    """Elimina la cuenta con su perfil profesional (si es cuidadora), familiares propios, chats,
    solicitudes, trabajos y reseñas. `force` permite eliminarla aunque tenga un trabajo activo
    (solo lo usa el equipo desde la Consola)."""
    uid = user.id
    profile = (await db.execute(select(models.CaregiverProfile)
                                .where(models.CaregiverProfile.user_id == uid))).scalars().first()
    pid = profile.id if profile else None

    if not force:
        if (await _has_active_engagement(db, family_user_id=uid)
                or (pid and await _has_active_engagement(db, caregiver_profile_id=pid))):
            raise conflict("ACTIVE_ENGAGEMENT",
                           "Tienes un trabajo en curso. Ciérralo antes de eliminar la cuenta.")

    paths: list[str | None] = [storage.path_from_url(user.avatar_url)]

    def mine(family_col, profile_col):
        return (family_col == uid) if pid is None else ((family_col == uid) | (profile_col == pid))

    # Chats
    conv_ids = (await db.execute(select(models.ChatConversation.id).where(
        mine(models.ChatConversation.family_user_id, models.ChatConversation.caregiver_profile_id)))).scalars().all()
    if conv_ids:
        await db.execute(delete(models.ChatMessage).where(models.ChatMessage.conversation_id.in_(conv_ids)))
        await db.execute(delete(models.ChatConversation).where(models.ChatConversation.id.in_(conv_ids)))
    # Solicitudes, trabajos y contactos
    await db.execute(delete(models.HireRequest).where(
        mine(models.HireRequest.family_user_id, models.HireRequest.caregiver_profile_id)))
    await db.execute(delete(models.CaregiverEngagement).where(
        mine(models.CaregiverEngagement.family_user_id, models.CaregiverEngagement.caregiver_profile_id)))
    await db.execute(delete(models.ContactRequest).where(
        mine(models.ContactRequest.family_user_id, models.ContactRequest.caregiver_profile_id)))
    # Reseñas escritas por la persona o recibidas por su perfil
    affected = set((await db.execute(select(models.CaregiverReview.caregiver_profile_id)
                                     .where(models.CaregiverReview.author_user_id == uid))).scalars().all())
    await db.execute(delete(models.CaregiverReview).where(models.CaregiverReview.author_user_id == uid))
    if pid:
        await db.execute(delete(models.CaregiverReview).where(models.CaregiverReview.caregiver_profile_id == pid))
        affected.discard(pid)
    await recalc_ratings(db, affected)
    # Perfil profesional y sus documentos
    if pid:
        docs = (await db.execute(select(models.CaregiverDocument)
                                 .where(models.CaregiverDocument.caregiver_profile_id == pid))).scalars().all()
        for d in docs:
            paths += [storage.path_from_url(d.file_url), storage.path_from_url(d.pending_file_url)]
        await db.execute(delete(models.CaregiverDocument).where(models.CaregiverDocument.caregiver_profile_id == pid))
        await db.execute(delete(models.CaregiverProfile).where(models.CaregiverProfile.id == pid))
    # Familiares: se eliminan los que solo ella tenía; en los compartidos solo se quita su acceso.
    memberships = (await db.execute(select(models.PatientMember)
                                    .where(models.PatientMember.user_id == uid))).scalars().all()
    for m in memberships:
        others = (await db.execute(select(func.count(models.PatientMember.id)).where(
            models.PatientMember.patient_id == m.patient_id, models.PatientMember.user_id != uid))).scalar_one()
        patient = await db.get(models.Patient, m.patient_id)
        if others == 0 and patient is not None:
            paths += await purge_patient(db, patient)
        else:
            await db.execute(delete(models.PatientMember).where(models.PatientMember.id == m.id))

    await db.execute(delete(models.RefreshSession).where(models.RefreshSession.user_id == uid))
    # Los clics a tiendas se conservan como cifra anónima (respaldan la comisión por referido).
    await db.execute(update(models.ProductClick).where(models.ProductClick.user_id == uid).values(user_id=None))
    await db.execute(delete(models.User).where(models.User.id == uid))
    return [p for p in paths if p]

