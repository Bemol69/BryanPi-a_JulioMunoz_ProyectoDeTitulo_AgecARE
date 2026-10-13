"""Notifica a la Consola de Administración los cambios del sitio público (perfil publicado,
reseñas, documentos) para que el staff los revise. Si la Consola no responde, el error se
registra pero no se propaga: lo que la persona hizo en el sitio no debe fallar por eso.

Las instancias de Vercel se "duermen", así que la primera llamada a la Consola puede demorar
varios segundos: timeout generoso y un reintento."""
import logging

import httpx

from app import models
from app.config import get_settings

log = logging.getLogger("agecare.sync")
TIMEOUT_SECONDS = 10.0


async def _post_to_admin(path: str, payload: dict) -> bool:
    settings = get_settings()
    headers = {"X-Internal-Key": settings.admin_sync_key}
    url = f"{settings.admin_sync_url}{path}"
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                res = await client.post(url, json=payload, headers=headers)
            if res.status_code < 400:
                return True
            if res.status_code < 500:  # 4xx: reintentar no sirve (p. ej. cuidadora aún no sincronizada)
                log.warning("La Consola rechazó %s: %s %s", path, res.status_code, res.text[:200])
                return False
            log.warning("La Consola respondió %s en %s (intento %s)", res.status_code, path, attempt)
        except httpx.HTTPError as exc:
            log.warning("No se pudo contactar a la Consola en %s (intento %s): %r", path, attempt, exc)
    return False


async def fetch_admin_documents(email: str) -> list[dict]:
    """Estado de los documentos de la cuidadora según la Consola ([] si no responde)."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get(f"{settings.admin_sync_url}/marketplace/caregivers/documents",
                                   params={"email": email}, headers={"X-Internal-Key": settings.admin_sync_key})
        if res.status_code == 200:
            return res.json().get("items", [])
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("No se pudo consultar los documentos en la Consola: %r", exc)
    return []


async def sync_caregiver_to_admin(profile: "models.CaregiverProfile", user: "models.User",
                                  is_engaged: bool = False) -> None:
    zones = profile.zones or []
    await _post_to_admin("/marketplace/caregivers/sync", {
        "external_user_id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "zone": zones[0] if zones else "Sin especificar",
        "specialties": profile.specialties or [],
        "languages": profile.languages or [],
        "certifications_count": len(profile.certifications or []),
        "is_engaged": is_engaged,
    })


async def sync_review_to_admin(caregiver_email: str, family_name: str, rating: int,
                               comment: str | None) -> None:
    """Reenvía una reseña a la Consola para que otorgue puntos de fidelización."""
    await _post_to_admin("/marketplace/reviews/sync", {
        "caregiver_email": caregiver_email, "family_name": family_name,
        "rating": rating, "comment": comment,
    })


async def sync_document_to_admin(caregiver_email: str, doc_type: str, file_url: str,
                                 original_filename: str, is_change: bool = False) -> None:
    """Reenvía un documento subido (cédula, antecedentes, certificado). `is_change` indica que
    reemplaza a uno ya aprobado: queda como cambio pendiente de aprobación, sin pisar el vigente."""
    await _post_to_admin("/marketplace/documents/sync", {
        "caregiver_email": caregiver_email, "doc_type": doc_type, "file_url": file_url,
        "original_filename": original_filename, "is_change": is_change,
    })
