"""Pacientes: crear y listar, para la vista de familia."""
from fastapi import APIRouter
from sqlalchemy import select

from app import models
from app.deps import CurrentUser, Db
from app.errors import forbidden, not_found
from app.schemas.common import Page
from app.schemas.patients import PatientCardOut, PatientCreateIn, PatientCreateOut, PatientOut

router = APIRouter(tags=["Pacientes"])


# ---------- 4.1 Crear paciente ----------
@router.post("/patients", response_model=PatientCreateOut, status_code=201)
async def create_patient(body: PatientCreateIn, db: Db, user: CurrentUser):
    if user.account_type != "family":
        raise forbidden("Solo una cuenta de familia puede crear el perfil de un adulto mayor.")
    patient = models.Patient(full_name=body.full_name, birth_date=body.birth_date, sex=body.sex,
                             photo_url=body.photo_url, conditions=body.conditions, notes=body.notes)
    db.add(patient)
    await db.flush()
    db.add(models.PatientMember(patient_id=patient.id, user_id=user.id, role="family", is_owner=True))
    return PatientCreateOut(patient_id=patient.id, full_name=patient.full_name, created_at=patient.created_at)


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
    member = (await db.execute(select(models.PatientMember).where(
        models.PatientMember.patient_id == patient_id,
        models.PatientMember.user_id == user.id))).scalar_one_or_none()
    if member is None:
        raise forbidden("No tienes acceso a este paciente.")
    p = await db.get(models.Patient, patient_id)
    if p is None:
        raise not_found()
    return PatientOut(patient_id=p.id, full_name=p.full_name, birth_date=p.birth_date, sex=p.sex,
                      photo_url=p.photo_url, conditions=p.conditions or [], notes=p.notes)
