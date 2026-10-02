"""Almacenamiento de archivos subidos (fotos de perfil, fotos de pacientes y documentos).

- Con GENERAL_SUPABASE_URL y GENERAL_SUPABASE_SERVICE_KEY configuradas, los archivos van a
  Supabase Storage (necesario en Vercel, donde el disco es de solo lectura).
- Sin ellas, se guardan en la carpeta local `uploads/` y los sirve la propia API (desarrollo).
"""
from pathlib import Path

import httpx

from app.config import get_settings
from app.errors import ApiError

LOCAL_ROOT = Path(__file__).resolve().parent.parent / "uploads"

# Vercel limita el cuerpo de una petición a 4,5 MB; 4 MB de archivo deja margen para el multipart.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_UPLOAD_LABEL = "4 MB"


def remote_enabled() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_service_key)


def _auth_headers() -> dict[str, str]:
    key = get_settings().supabase_service_key
    headers = {"apikey": key}
    if key.startswith("eyJ"):  # llave legacy (JWT): también va como Bearer
        headers["Authorization"] = f"Bearer {key}"
    return headers


async def save(path: str, data: bytes, content_type: str, base_url: str,
               stale: list[str] | None = None) -> str:
    """Guarda `data` en `path` (p. ej. "avatars/<id>.png") y devuelve su URL pública.
    `stale` son rutas de versiones anteriores del mismo archivo (otra extensión) a borrar."""
    stale = stale or []
    if not remote_enabled():
        target = LOCAL_ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        for old in stale:
            (LOCAL_ROOT / old).unlink(missing_ok=True)
        target.write_bytes(data)
        return f"{base_url.rstrip('/')}/uploads/{path}"

    s = get_settings()
    root = s.supabase_url.rstrip("/")
    bucket = s.storage_bucket
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            put = lambda: client.post(f"{root}/storage/v1/object/{bucket}/{path}", content=data,
                                      headers={**headers, "Content-Type": content_type, "x-upsert": "true"})
            res = await put()
            if res.status_code in (400, 404) and "bucket" in res.text.lower():
                # Primera subida: crea el bucket público y reintenta.
                await client.post(f"{root}/storage/v1/bucket", headers=headers,
                                  json={"id": bucket, "name": bucket, "public": True})
                res = await put()
            if res.status_code >= 300:
                raise ApiError(502, "STORAGE_ERROR", "No se pudo guardar el archivo. Intenta nuevamente.")
            if stale:
                await client.request("DELETE", f"{root}/storage/v1/object/{bucket}", headers=headers,
                                     json={"prefixes": stale})
    except httpx.HTTPError:
        raise ApiError(502, "STORAGE_ERROR", "No se pudo guardar el archivo. Intenta nuevamente.")
    return f"{root}/storage/v1/object/public/{bucket}/{path}"
