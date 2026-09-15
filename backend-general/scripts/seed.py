"""Seed de datos demo para la API general.

Uso: python -m scripts.seed
Credenciales demo:
    familia@demo.cl / Familia123!   (cuenta de familia, con un paciente creado)
    maria@cuidado.cl / Cuidado123!  (cuenta de cuidadora, publicada en el marketplace)
"""
import asyncio
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete

from app import models
from app.database import Base, get_engine, get_session_factory
from app.security import hash_password

random.seed(20260909)
NOW = datetime.now(timezone.utc)

CAREGIVERS = [
    dict(full_name="María Torres", email="maria@cuidado.cl", headline="Cuidadora certificada · 8 años de experiencia",
        years_experience=8, specialties=["Alzheimer", "Movilidad reducida", "Posoperatorio"],
        languages=["Español"], zones=["Providencia", "Ñuñoa"],
        certifications=[{"name": "Cuidados geriátricos", "issuer": "INACAP", "year": 2019}],
        rating_seed=[5, 5, 4, 5], featured=True),
    dict(full_name="Javiera Soto", email="javiera@cuidado.cl", headline="Enfermera geriátrica · turnos nocturnos",
        years_experience=6, specialties=["Cuidados paliativos", "Control de medicación"],
        languages=["Español", "Inglés"], zones=["Las Condes"],
        certifications=[{"name": "Enfermería geriátrica", "issuer": "U. de Chile", "year": 2020}],
        rating_seed=[5, 4, 5], featured=True),
    dict(full_name="Rocío Álvarez", email="rocio@cuidado.cl", headline="Acompañamiento y estimulación cognitiva",
        years_experience=4, specialties=["Estimulación cognitiva", "Acompañamiento"],
        languages=["Español"], zones=["Maipú"],
        certifications=[], rating_seed=[5, 5], featured=False),
    dict(full_name="Fernanda Ibáñez", email="fernanda@cuidado.cl", headline="Cuidadora de día, experiencia con Alzheimer",
        years_experience=5, specialties=["Alzheimer"], languages=["Español"], zones=["Providencia"],
        certifications=[], rating_seed=[4, 5, 5], featured=False),
]

PRODUCTS = [
    dict(name="Andadera plegable con ruedas", category="mobility", price_range="$40.000 - $60.000",
        description="Andadera de aluminio ligera, plegable, con ruedas delanteras y asiento de descanso. "
                    "Soporta hasta 130 kg.", external_url="https://ortochile.cl/andadera-plegable"),
    dict(name="Dispensador de pastillas semanal", category="daily_care", price_range="$15.000 - $25.000",
        description="Organizador de medicamentos de 7 días con 4 tomas diarias y alarma sonora programable.",
        external_url="https://saludhogar.cl/pastillero"),
    dict(name="Barra de baño de seguridad", category="home_safety", price_range="$20.000 - $35.000",
        description="Barra de sujeción antideslizante para regadera o tina. Instalación con ventosas de fijación rápida.",
        external_url="https://saludhogar.cl/barra-bano"),
    dict(name="Monitor de signos vitales portátil", category="monitoring", price_range="$50.000 - $90.000",
        description="Oxímetro y monitor de frecuencia cardíaca portátil, pantalla grande, fácil de leer.",
        external_url="https://ortochile.cl/monitor-vitales"),
]

FAMILY_REVIEW_NAMES = ["Familia Pérez", "Familia González", "Familia Rojas", "Familia Silva"]


async def seed() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_session_factory()() as db:
        for table in (models.ContactRequest, models.CaregiverReview, models.CaregiverProfile,
                     models.PatientMember, models.Patient, models.MarketProduct,
                     models.RefreshSession, models.User):
            await db.execute(delete(table))

        # ---- Productos ----
        for p in PRODUCTS:
            db.add(models.MarketProduct(name=p["name"], category=p["category"],
                                        description=p["description"], price_range=p["price_range"],
                                        external_url=p["external_url"]))

        # ---- Cuidadoras ----
        for c in CAREGIVERS:
            user = models.User(full_name=c["full_name"], email=c["email"],
                               password_hash=hash_password("Cuidado123!"), account_type="caregiver")
            db.add(user)
            await db.flush()
            profile = models.CaregiverProfile(
                user_id=user.id, headline=c["headline"], bio=f"Soy {c['full_name']}, cuidadora con vocación "
                "de servicio. Me dedico al cuidado de adultos mayores con paciencia, cariño y responsabilidad.",
                years_experience=c["years_experience"], specialties=c["specialties"],
                languages=c["languages"], zones=c["zones"], certifications=c["certifications"],
                is_listed=True, is_featured=c["featured"])
            db.add(profile)
            await db.flush()
            for i, rating in enumerate(c["rating_seed"]):
                db.add(models.CaregiverReview(
                    caregiver_profile_id=profile.id,
                    author_user_id=user.id,  # placeholder: reseñas demo, no de un familiar real
                    author_name=random.choice(FAMILY_REVIEW_NAMES), rating=rating,
                    comment="Muy puntual y profesional." if rating >= 5 else "Buen trato en general.",
                    created_at=NOW - timedelta(days=random.randint(1, 60))))
            profile.rating_avg = round(sum(c["rating_seed"]) / len(c["rating_seed"]), 2)
            profile.reviews_count = len(c["rating_seed"])

        # ---- Familia demo con un paciente ----
        family = models.User(full_name="Carolina Muñoz", email="familia@demo.cl",
                             password_hash=hash_password("Familia123!"), account_type="family")
        db.add(family)
        await db.flush()
        patient = models.Patient(full_name="Elena Muñoz", birth_date=date(1948, 3, 12), sex="female",
                                 conditions=["Movilidad reducida"], notes="Le gusta la música y el jardín.")
        db.add(patient)
        await db.flush()
        db.add(models.PatientMember(patient_id=patient.id, user_id=family.id, role="family", is_owner=True))

        await db.commit()
        print(f"Seed completado: {len(CAREGIVERS)} cuidadoras publicadas, 1 familia demo, {len(PRODUCTS)} productos.")


if __name__ == "__main__":
    asyncio.run(seed())
