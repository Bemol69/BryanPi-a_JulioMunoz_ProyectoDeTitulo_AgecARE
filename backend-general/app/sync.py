"""Notifica a la Consola de Administración cuando una cuidadora publica su
perfil, para que quede pendiente de revisión. Falla en silencio si la
Consola no está disponible."""
import httpx

from app import models
from app.config import get_settings


async def sync_caregiver_to_admin(profile: "models.CaregiverProfile", user: "models.User",
                                  is_engaged: bool = False) -> None:
    settings = get_settings()
    zones = profile.zones or []
    payload = {
        "external_user_id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "zone": zones[0] if zones else "Sin especificar",
        "specialties": profile.specialties or [],
        "languages": profile.languages or [],
        "certifications_count": len(profile.certifications or []),
        "is_engaged": is_engaged,
    }
    headers = {"X-Internal-Key": settings.admin_sync_key}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{settings.admin_sync_url}/marketplace/caregivers/sync",
                              json=payload, headers=headers)
    except httpx.HTTPError:
        pass


async def sync_review_to_admin(caregiver_email: str, family_name: str, rating: int,
                               comment: str | None) -> None:
    """Reenvía a la Consola de Administración una reseña dejada en el sitio
    público, para que se reflejen en el ranking y los puntos de fidelización.
    Falla en silencio si la Consola no está disponible o no conoce aún a la
    cuidadora (todavía no sincronizada)."""
    settings = get_settings()
    payload = {
        "caregiver_email": caregiver_email,
        "family_name": family_name,
        "rating": rating,
        "comment": comment,
    }
    headers = {"X-Internal-Key": settings.admin_sync_key}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{settings.admin_sync_url}/marketplace/reviews/sync",
                              json=payload, headers=headers)
    except httpx.HTTPError:
        pass


async def sync_document_to_admin(caregiver_email: str, doc_type: str, file_url: str,
                                 original_filename: str) -> None:
    """Reenvía a la Consola de Administración un documento que la cuidadora
    subió (cédula, certificado de antecedentes, certificados de cursos), para
    que el staff pueda revisarlo antes de aprobar el perfil. Falla en
    silencio si la Consola no está disponible o no conoce aún a la cuidadora."""
    settings = get_settings()
    payload = {
        "caregiver_email": caregiver_email,
        "doc_type": doc_type,
        "file_url": file_url,
        "original_filename": original_filename,
    }
    headers = {"X-Internal-Key": settings.admin_sync_key}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{settings.admin_sync_url}/marketplace/documents/sync",
                              json=payload, headers=headers)
    except httpx.HTTPError:
        pass
