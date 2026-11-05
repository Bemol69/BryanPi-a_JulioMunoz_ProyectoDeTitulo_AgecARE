"""Almacenamiento de archivos subidos (fotos de perfil, fotos de pacientes y documentos).

- Con GENERAL_SUPABASE_URL y GENERAL_SUPABASE_SERVICE_KEY configuradas, los archivos van a
  Supabase Storage (necesario en Vercel, donde el disco es de solo lectura).
- Sin ellas, se guardan en la carpeta local `uploads/` y los sirve la propia API (desarrollo).
"""
import logging
from pathlib import Path

import httpx

from app.config import get_settings
from app.errors import ApiError

LOCAL_ROOT = Path(__file__).resolve().parent.parent / "uploads"

# Vercel limita el cuerpo de una petición a 4,5 MB; 4 MB de archivo deja margen para el multipart.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_UPLOAD_LABEL = "4 MB"


_PNG = bytes.fromhex("89504e470d0a1a0a")
_JPEG = bytes.fromhex("ffd8ff")


def check_signature(data: bytes, content_type: str) -> None:
    """El tipo que declara el navegador no es de fiar: se comprueba que el contenido sea realmente
    una imagen PNG, JPG o WEBP, o un PDF, antes de guardarlo."""
    if content_type == "image/png":
        ok = data.startswith(_PNG)
    elif content_type == "image/jpeg":
        ok = data.startswith(_JPEG)
    elif content_type == "image/webp":
        ok = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif content_type == "application/pdf":
        ok = data.startswith(b"%PDF-")
    else:
        ok = False
    if not ok:
        raise ApiError(422, "INVALID_FILE_TYPE", "El archivo no corresponde al formato indicado (PDF, JPG, PNG o WEBP).")


def path_from_url(url: str | None) -> str | None:
    """Ruta dentro del almacenamiento (p. ej. "avatars/<id>.png") a partir de la URL pública guardada."""
    if not url:
        return None
    url = url.split("?")[0]
    for marker in ("/object/public/", "/uploads/"):
        i = url.find(marker)
        if i >= 0:
            rest = url[i + len(marker):]
            if marker == "/object/public/":  # el primer tramo es el nombre del bucket
                rest = rest.split("/", 1)[1] if "/" in rest else ""
            return rest or None
    return None


async def delete(paths: list[str]) -> None:
    """Borra archivos subidos. Es un esfuerzo razonable: si falla no se detiene lo que la persona pidió."""
    paths = [p for p in paths if p and ".." not in p]
    if not paths:
        return
    if not remote_enabled():
        for p in paths:
            (LOCAL_ROOT / p).unlink(missing_ok=True)
        return
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            await client.request("DELETE", f"{s.supabase_url.rstrip('/')}/storage/v1/object/{s.storage_bucket}",
                                 headers=_auth_headers(), json={"prefixes": paths})
    except httpx.HTTPError as exc:
        logging.getLogger("agecare.storage").warning("No se pudieron borrar archivos: %r", exc)


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
