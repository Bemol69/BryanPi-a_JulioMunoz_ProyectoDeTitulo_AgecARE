"""Autenticación y cuenta de usuario."""
from datetime import timedelta

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select

from app import accounts, models, storage
from app.deps import CurrentUser, Db
from app.config import get_settings
from app.errors import ApiError, conflict, unauthorized
from app.schemas.auth import (AuthOut, DeleteAccountIn, LoginIn, MembershipOut, RefreshIn, RefreshOut,
                              RegisterIn, UserOut, UserPatchIn)
from app.sync import remove_caregiver_from_admin, sync_caregiver_to_admin
from app.security import (as_utc, create_access_token, ahash_password, averify_password, hash_refresh,
                          new_refresh_token, now_utc)

router = APIRouter(tags=["Autenticación"])

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
    # El hash va primero: así no se retiene una conexión a la base mientras se espera el turno de la CPU.
    password_hash = await ahash_password(body.password)
    exists = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one_or_none()
    if exists:
        raise conflict("EMAIL_ALREADY_EXISTS", "Ya existe una cuenta con este correo electrónico.")

    phone = body.phone.strip() if body.phone else None
    if phone:
        phone_exists = (await db.execute(
            select(models.User).where(models.User.phone == phone))).scalar_one_or_none()
        if phone_exists:
            raise conflict("PHONE_ALREADY_EXISTS", "Ya existe una cuenta con este número de teléfono.")

    user = models.User(full_name=body.full_name, email=email, password_hash=password_hash,
                       phone=phone, locale=body.locale, account_type=body.account_type)
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
_DUMMY_HASH: str | None = None


async def _burn_hash_time(password: str) -> None:
    """Si el correo no existe se hace igual el cálculo del hash: así no se nota por el tiempo de respuesta."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = await ahash_password("relleno-para-igualar-tiempos")
    await averify_password(password, _DUMMY_HASH)


@router.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn, db: Db):
    s = get_settings()
    email = body.email.lower()
    user = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one_or_none()
    await db.commit()  # termina la lectura y devuelve la conexión: lo que sigue (el hash) es solo CPU

    # Cuenta bloqueada: ni se mira la contraseña (así tampoco se puede seguir probando).
    if user is not None and user.locked_until and as_utc(user.locked_until) > now_utc():
        raise ApiError(423, "ACCOUNT_LOCKED",
                       f"Cuenta bloqueada temporalmente por intentos fallidos. Intenta en {s.lockout_minutes} minutos.")

    if user is None:
        await _burn_hash_time(body.password)
    if user is None or not await averify_password(body.password, user.password_hash):
        if user is not None:
            user.failed_attempts += 1
            if user.failed_attempts >= s.max_login_attempts:
                user.locked_until = now_utc() + timedelta(minutes=s.lockout_minutes)
                user.failed_attempts = 0
            # Se guarda ahora: al lanzar el error la sesión se revierte y el intento fallido se perdería.
            await db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")

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
        phone = body.phone.strip() or None
        if phone and phone != user.phone:
            phone_exists = (await db.execute(select(models.User).where(
                models.User.phone == phone, models.User.id != user.id))).scalar_one_or_none()
            if phone_exists:
                raise conflict("PHONE_ALREADY_EXISTS", "Ya existe una cuenta con este número de teléfono.")
        user.phone = phone
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.locale is not None:
        user.locale = body.locale
    memberships = await _memberships_for(db, user.id)
    return _user_out(user, memberships)


# ---------- Eliminar mi cuenta ----------
@router.delete("/users/me", status_code=204)
async def delete_me(body: DeleteAccountIn, db: Db, user: CurrentUser):
    """Elimina la cuenta con todo lo que cuelga de ella. Pide la contraseña para evitar errores."""
    if not await averify_password(body.password, user.password_hash):
        raise ApiError(403, "WRONG_PASSWORD", "La contraseña no es correcta.")
    email, was_caregiver = user.email, user.account_type == "caregiver"
    paths = await accounts.purge_user(db, user)
    await db.flush()
    await storage.delete(paths)
    if was_caregiver:  # también desaparece de la Consola
        await db.commit()  # se guarda y la conexión vuelve al grupo mientras se espera a la otra API
        await remove_caregiver_from_admin(email)


# ---------- Foto de perfil ----------
@router.post("/users/me/avatar", response_model=UserOut)
async def upload_avatar(request: Request, db: Db, user: CurrentUser, file: UploadFile = File(...)):
    ext = AVATAR_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise ApiError(422, "INVALID_FILE_TYPE", "La foto debe ser JPG, PNG o WEBP.")
    data = await file.read()
    if len(data) > storage.MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", f"La foto no puede superar los {storage.MAX_UPLOAD_LABEL}.")
    storage.check_signature(data, file.content_type)

    url = await storage.save(f"avatars/{user.id}{ext}", data, file.content_type, str(request.base_url),
                             stale=[f"avatars/{user.id}{e}" for e in AVATAR_CONTENT_TYPES.values() if e != ext])
    user.avatar_url = f"{url}?v={int(now_utc().timestamp())}"
    if user.account_type == "caregiver":
        # La Consola muestra la foto de cada cuidadora: se le avisa del cambio.
        profile = (await db.execute(select(models.CaregiverProfile)
                                    .where(models.CaregiverProfile.user_id == user.id))).scalars().first()
        if profile is not None:
            engaged = (await db.execute(select(models.CaregiverEngagement.id).where(
                models.CaregiverEngagement.caregiver_profile_id == profile.id,
                models.CaregiverEngagement.status == "active").limit(1))).first() is not None
            await db.commit()  # se guarda y la conexión vuelve al grupo mientras se espera a la otra API
            await sync_caregiver_to_admin(profile, user, engaged)
    memberships = await _memberships_for(db, user.id)
    return _user_out(user, memberships)
