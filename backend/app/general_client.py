"""Llamadas de la Consola a la API del sitio público (con la clave compartida X-Internal-Key).

Cuando el staff aprueba/suspende un perfil o revisa un documento, el sitio público debe
enterarse: de eso depende quién aparece en el marketplace. Si el aviso falla, la acción se
cancela (se responde 502) para que el staff la repita, en vez de dejar los dos sistemas
desincronizados. Si GENERAL_SYNC_URL no está configurada (desarrollo sin el sitio) no se avisa."""
import logging

import httpx

from app.config import get_settings
from app.errors import ApiError

log = logging.getLogger("agecare.general")
TIMEOUT_SECONDS = 10.0


def enabled() -> bool:
    return bool(get_settings().general_sync_url)


def _headers() -> dict[str, str]:
    return {"X-Internal-Key": get_settings().internal_sync_key}


async def _call(method: str, path: str, *, attempts: int = 2, timeout: float = TIMEOUT_SECONDS,
                **kwargs) -> httpx.Response | None:
    url = f"{get_settings().general_sync_url.rstrip('/')}{path}"
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.request(method, url, headers=_headers(), **kwargs)
            if res.status_code < 500:
                return res
            log.warning("El sitio público respondió %s en %s (intento %s)", res.status_code, path, attempt)
        except httpx.HTTPError as exc:
            log.warning("No se pudo contactar al sitio público en %s (intento %s): %r", path, attempt, exc)
    return None


def _sync_failed() -> ApiError:
    return ApiError(502, "GENERAL_SYNC_FAILED",
                    "No se pudo avisar al sitio público. No se guardó el cambio; intenta nuevamente en unos segundos.")


async def push_status(email: str, status: str) -> None:
    """Estado del perfil (pending | approved | suspended) para que el marketplace lo respete."""
    if not enabled():
        return
    res = await _call("POST", "/internal/caregivers/status", json={"email": email, "status": status})
    # 404 = la cuidadora aún no existe en el sitio (perfil de prueba): no bloquea al staff.
    if res is None or (res.status_code >= 400 and res.status_code != 404):
        raise _sync_failed()


async def push_document_review(email: str, doc_type: str, action: str, note: str | None) -> None:
    if not enabled():
        return
    res = await _call("POST", "/internal/documents/review",
                      json={"email": email, "doc_type": doc_type, "action": action, "note": note})
    if res is None or (res.status_code >= 400 and res.status_code != 404):
        raise _sync_failed()


async def fetch_documents(email: str) -> list[dict] | None:
    """Documentos de la cuidadora tal como están en el sitio público (None si no se pudo consultar)."""
    if not enabled():
        return None
    res = await _call("GET", "/internal/caregivers/documents", attempts=1, timeout=6.0,
                      params={"email": email})
    if res is None or res.status_code != 200:
        return None
    return res.json()
