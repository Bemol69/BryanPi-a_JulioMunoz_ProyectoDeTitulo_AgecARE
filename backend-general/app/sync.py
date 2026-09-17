"""Notifica a la Consola de Administración cuando una cuidadora publica su
perfil, para que quede pendiente de revisión. Falla en silencio si la
Consola no está disponible."""
import httpx

from app import models
from app.config import get_settings


async def sync_caregiver_to_admin(profile: "models.CaregiverProfile", user: "models.User") -> None:
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
