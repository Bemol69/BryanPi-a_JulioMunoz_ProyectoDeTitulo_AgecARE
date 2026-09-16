"""Autenticación y cuenta de usuario."""
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select

from app import models
from app.deps import CurrentUser, Db
from app.config import get_settings
from app.errors import ApiError, conflict, unauthorized
from app.schemas.auth import (AuthOut, LoginIn, MembershipOut, RefreshIn, RefreshOut,
                              RegisterIn, UserOut, UserPatchIn)
from app.security import (as_utc, create_access_token, hash_password, hash_refresh,
                          new_refresh_token, now_utc, verify_password)

router = APIRouter(tags=["Autenticación"])

AVATAR_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "avatars"
AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


async def _memberships_for(db: Db, user_id) -> list[MembershipOut]:
    rows = (await db.execute(
        select(models.PatientMember).where(models.PatientMember.user_id == user_id))).scalars().all()
    return [MembershipOut(patient_id=m.patient_id, patient_name=m.patient.full_name, role=m.role)
           for m in rows]


def _user_out(user: models.User, memberships: list[MembershipOut]) -> UserOut:
    return UserOut(user_id=user.id, full_name=user.full_name, email=user.email, phone=user.phone,
                  avatar_url=user.avatar_url, locale=user.locale, account_type=user.account_type,
                  memberships=memberships)


# ---------- 3.1 Registrar cuenta ----------
@router.post("/auth/register", response_model=AuthOut, status_code=201)
async def register(body: RegisterIn, db: Db):
    email = body.email.lower()
    exists = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one_or_none()
    if exists:
        raise conflict("EMAIL_ALREADY_EXISTS", "Ya existe una cuenta con este correo electrónico.")

    user = models.User(full_name=body.full_name, email=email, password_hash=hash_password(body.password),
                       phone=body.phone, locale=body.locale, account_type=body.account_type)
    db.add(user)
    await db.flush()

    if body.account_type == "caregiver":
        db.add(models.CaregiverProfile(user_id=user.id))

    token, refresh_hash, expires = new_refresh_token()
    db.add(models.RefreshSession(user_id=user.id, refresh_hash=refresh_hash, expires_at=expires))
    await db.flush()

    return AuthOut(access_token=create_access_token(user.id), refresh_token=token,
                  user=_user_out(user, []))


# ---------- 3.2 Iniciar sesión ----------
@router.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn, db: Db):
    s = get_settings()
    email = body.email.lower()
    user = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        if user is not None:
            user.failed_attempts += 1
            if user.failed_attempts >= s.max_login_attempts:
                user.locked_until = now_utc() + timedelta(minutes=s.lockout_minutes)
                user.failed_attempts = 0
        raise ApiError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")
    if user.locked_until and as_utc(user.locked_until) > now_utc():
        raise ApiError(423, "ACCOUNT_LOCKED",
                       "Cuenta bloqueada temporalmente por intentos fallidos. Intenta en 15 minutos.")

    user.failed_attempts = 0
    user.locked_until = None

    token, refresh_hash, expires = new_refresh_token()
    db.add(models.RefreshSession(user_id=user.id, refresh_hash=refresh_hash, expires_at=expires))

    memberships = await _memberships_for(db, user.id)
    return AuthOut(access_token=create_access_token(user.id), refresh_token=token,
                  user=_user_out(user, memberships))


# ---------- 3.3 Refrescar token ----------
@router.post("/auth/refresh", response_model=RefreshOut)
async def refresh(body: RefreshIn, db: Db):
    session = (await db.execute(select(models.RefreshSession)
                                .where(models.RefreshSession.refresh_hash == hash_refresh(body.refresh_token)))
              ).scalar_one_or_none()
    if session is None or as_utc(session.expires_at) < now_utc():
        raise unauthorized("La sesión no es válida o fue revocada. Inicia sesión de nuevo.",
                           "INVALID_REFRESH_TOKEN")
    if session.revoked_at is not None:
        others = (await db.execute(select(models.RefreshSession).where(
            models.RefreshSession.user_id == session.user_id,
            models.RefreshSession.revoked_at.is_(None)))).scalars()
        for s_ in others:
            s_.revoked_at = now_utc()
        raise unauthorized("La sesión no es válida o fue revocada. Inicia sesión de nuevo.",
                           "INVALID_REFRESH_TOKEN")

    user = await db.get(models.User, session.user_id)
    if user is None:
        raise unauthorized("La sesión no es válida o fue revocada. Inicia sesión de nuevo.",
                           "INVALID_REFRESH_TOKEN")

    token, refresh_hash, expires = new_refresh_token()
    new_session = models.RefreshSession(user_id=user.id, refresh_hash=refresh_hash, expires_at=expires)
    db.add(new_session)
    await db.flush()
    session.revoked_at = now_utc()
    session.rotated_to = new_session.id
    return RefreshOut(access_token=create_access_token(user.id), refresh_token=token)


# ---------- 3.4 Cerrar sesión ----------
@router.post("/auth/logout", status_code=204)
async def logout(body: RefreshIn, db: Db, user: CurrentUser):
    session = (await db.execute(select(models.RefreshSession).where(
        models.RefreshSession.refresh_hash == hash_refresh(body.refresh_token),
        models.RefreshSession.user_id == user.id))).scalar_one_or_none()
    if session is not None:
        session.revoked_at = now_utc()


# ---------- 3.7 Obtener mi perfil ----------
@router.get("/users/me", response_model=UserOut)
async def me(db: Db, user: CurrentUser):
    memberships = await _memberships_for(db, user.id)
    return _user_out(user, memberships)


# ---------- 3.8 Actualizar mi perfil ----------
@router.patch("/users/me", response_model=UserOut)
async def patch_me(body: UserPatchIn, db: Db, user: CurrentUser):
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.locale is not None:
        user.locale = body.locale
    memberships = await _memberships_for(db, user.id)
    return _user_out(user, memberships)


# ---------- Foto de perfil ----------
@router.post("/users/me/avatar", response_model=UserOut)
async def upload_avatar(request: Request, db: Db, user: CurrentUser, file: UploadFile = File(...)):
    ext = AVATAR_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise ApiError(422, "INVALID_FILE_TYPE", "La foto debe ser JPG, PNG o WEBP.")
    data = await file.read()
    if len(data) > AVATAR_MAX_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "La foto no puede superar los 5 MB.")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}{ext}"
    for stale_ext in AVATAR_CONTENT_TYPES.values():
        if stale_ext != ext:
            (AVATAR_DIR / f"{user.id}{stale_ext}").unlink(missing_ok=True)
    (AVATAR_DIR / filename).write_bytes(data)

    user.avatar_url = f"{str(request.base_url).rstrip('/')}/uploads/avatars/{filename}?v={int(now_utc().timestamp())}"
    memberships = await _memberships_for(db, user.id)
    return _user_out(user, memberships)
