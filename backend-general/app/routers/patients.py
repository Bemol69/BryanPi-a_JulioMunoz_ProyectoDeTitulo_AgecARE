"""Pacientes: crear y listar, para la vista de familia."""
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from sqlalchemy import select

from app import models
from app.deps import CurrentUser, Db
from app.errors import ApiError, forbidden, not_found
from app.schemas.common import Page
from app.schemas.patients import PatientCardOut, PatientCreateIn, PatientCreateOut, PatientOut
from app.security import now_utc

router = APIRouter(tags=["Pacientes"])

PHOTO_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "patients"
PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


# ---------- 4.1 Crear paciente ----------
@router.post("/patients", response_model=PatientCreateOut, status_code=201)
async def create_patient(body: PatientCreateIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede crear el perfil de un adulto mayor.")
    patient = models.Patient(full_name=body.full_name, birth_date=body.birth_date, sex=body.sex,
                             photo_url=body.photo_url, conditions=body.conditions,
                             medication_allergies=body.medication_allergies,
                             food_allergies=body.food_allergies, notes=body.notes)
    db.add(patient)
    await db.flush()
    db.add(models.PatientMember(patient_id=patient.id, user_id=user.id, role="family", is_owner=True))
    return PatientCreateOut(patient_id=patient.id, full_name=patient.full_name, created_at=patient.created_at)


async def _member_patient(db: Db, patient_id, user: models.User) -> models.Patient:
    member = (await db.execute(select(models.PatientMember).where(
        models.PatientMember.patient_id == patient_id,
        models.PatientMember.user_id == user.id))).scalar_one_or_none()
    if member is None:
        raise forbidden("No tienes acceso a este paciente.")
    p = await db.get(models.Patient, patient_id)
    if p is None:
        raise not_found()
    return p


# ---------- Foto del adulto mayor ----------
@router.post("/patients/{patient_id}/photo", response_model=PatientOut)
async def upload_patient_photo(patient_id, request: Request, db: Db, user: CurrentUser,
                               file: UploadFile = File(...)):
    patient = await _member_patient(db, patient_id, user)
    ext = PHOTO_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise ApiError(422, "INVALID_FILE_TYPE", "La foto debe ser JPG, PNG o WEBP.")
    data = await file.read()
    if len(data) > PHOTO_MAX_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "La foto no puede superar los 5 MB.")

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{patient.id}{ext}"
    for stale_ext in PHOTO_CONTENT_TYPES.values():
        if stale_ext != ext:
            (PHOTO_DIR / f"{patient.id}{stale_ext}").unlink(missing_ok=True)
    (PHOTO_DIR / filename).write_bytes(data)

    patient.photo_url = f"{str(request.base_url).rstrip('/')}/uploads/patients/{filename}?v={int(now_utc().timestamp())}"
    return PatientOut(patient_id=patient.id, full_name=patient.full_name, birth_date=patient.birth_date,
                      sex=patient.sex, photo_url=patient.photo_url, conditions=patient.conditions or [],
                      medication_allergies=patient.medication_allergies or [],
                      food_allergies=patient.food_allergies or [], notes=patient.notes)


# ---------- 4.2 Listar mis pacientes ----------
@router.get("/patients", response_model=Page[PatientCardOut])
async def list_patients(db: Db, user: CurrentUser):
    rows = (await db.execute(select(models.PatientMember)
                             .where(models.PatientMember.user_id == user.id))).scalars().all()
    items = [PatientCardOut(patient_id=m.patient_id, full_name=m.patient.full_name,
                            photo_url=m.patient.photo_url, role=m.role) for m in rows]
    return Page(items=items, total=len(items))


# ---------- 4.3 Detalle de paciente ----------
@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(patient_id, db: Db, user: CurrentUser):
    p = await _member_patient(db, patient_id, user)
    return PatientOut(patient_id=p.id, full_name=p.full_name, birth_date=p.birth_date, sex=p.sex,
                      photo_url=p.photo_url, conditions=p.conditions or [],
                      medication_allergies=p.medication_allergies or [],
                      food_allergies=p.food_allergies or [], notes=p.notes)
