"""Seed de datos demo para la API general.

Uso: python -m scripts.seed
Credenciales demo:
    familia@demo.cl / Familia123!   (cuenta de familia, con un paciente creado)
    maria@cuidado.cl / Cuidado123!  (cuenta de cuidadora, publicada en el marketplace)
"""
import asyncio
import os
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app import models
from app.database import Base, get_engine, get_session_factory
from app.security import hash_password

random.seed(20260909)
# Fotos de demostración (ilustraciones de la carpeta webapp/public/demo/avatars). En producción, la dirección
# del sitio publicado; en desarrollo, el servidor local de la web.
AVATAR_BASE = os.getenv("DEMO_AVATAR_BASE", "http://localhost:5174").rstrip("/")
NOW = datetime.now(timezone.utc)

CAREGIVERS = [
    dict(slug="maria", full_name="María Torres", email="maria@cuidado.cl", headline="Cuidadora certificada · 8 años de experiencia",
        years_experience=8, specialties=["Alzheimer", "Movilidad reducida", "Posoperatorio"],
        languages=["Español"], zones=["Providencia", "Ñuñoa"],
        certifications=[{"name": "Cuidados geriátricos", "issuer": "INACAP", "year": 2019}],
        rating_seed=[5, 5, 4, 5], featured=True),
    dict(slug="javiera", full_name="Javiera Soto", email="javiera@cuidado.cl", headline="Enfermera geriátrica · turnos nocturnos",
        years_experience=6, specialties=["Cuidados paliativos", "Control de medicación"],
        languages=["Español", "Inglés"], zones=["Las Condes"],
        certifications=[{"name": "Enfermería geriátrica", "issuer": "U. de Chile", "year": 2020}],
        rating_seed=[5, 4, 5], featured=True),
    dict(slug="rocio", full_name="Rocío Álvarez", email="rocio@cuidado.cl", headline="Acompañamiento y estimulación cognitiva",
        years_experience=4, specialties=["Estimulación cognitiva", "Acompañamiento"],
        languages=["Español"], zones=["Maipú"],
        certifications=[], rating_seed=[5, 5], featured=False),
    dict(slug="fernanda", full_name="Fernanda Ibáñez", email="fernanda@cuidado.cl", headline="Cuidadora de día, experiencia con Alzheimer",
        years_experience=5, specialties=["Alzheimer"], languages=["Español"], zones=["Providencia"],
        certifications=[], rating_seed=[4, 5, 5], featured=False),
    dict(slug="sebastian", full_name="Sebastián Rivas", email="sebastian@cuidado.cl",
        headline="Técnico en enfermería · turnos de día", years_experience=7,
        specialties=["Movilidad reducida", "Posoperatorio", "Control de medicación"],
        languages=["Español"], zones=["Santiago Centro", "Estación Central"],
        certifications=[{"name": "Técnico en enfermería", "issuer": "Duoc UC", "year": 2018}],
        rating_seed=[5, 4, 5, 5], featured=False),
    dict(slug="andres", full_name="Andrés Pizarro", email="andres@cuidado.cl",
        headline="Cuidador con experiencia en demencia y acompañamiento", years_experience=10,
        specialties=["Demencia", "Acompañamiento"], languages=["Español"], zones=["La Florida", "Puente Alto"],
        certifications=[], rating_seed=[5, 5, 4], featured=False),
]

# Catálogo demo. El id sale del slug, igual que en la Consola (backend/scripts/seed.py): así
# el mismo producto es el mismo en los dos sistemas y los clics se pueden asociar.
def product_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"agecare:product:{slug}")


PRODUCTS = [
    dict(slug="andadera-plegable", name="Andadera plegable con ruedas", category="mobility", vendor="OrtoChile",
         price_clp=54990, sponsored=True, conditions=["Movilidad reducida", "Posoperatorio"],
         description="Andadera de aluminio ligera, plegable, con ruedas delanteras y asiento de descanso. "
                     "Soporta hasta 130 kg.", external_url="https://ortochile.cl/andadera-plegable"),
    dict(slug="baston-4-puntas", name="Bastón ortopédico de 4 puntas", category="mobility", vendor="OrtoChile",
         price_clp=14990, sponsored=False, conditions=["Movilidad reducida"],
         description="Bastón regulable en altura con base de cuatro apoyos: se sostiene solo y da más estabilidad.",
         external_url="https://ortochile.cl/baston-cuatro-puntas"),
    dict(slug="pastillero-semanal", name="Dispensador de pastillas semanal", category="daily_care", vendor="SaludHogar",
         price_clp=19990, sponsored=False, conditions=["Control de medicación", "Diabetes", "Hipertensión"],
         description="Organizador de medicamentos de 7 días con 4 tomas diarias y alarma sonora programable.",
         external_url="https://saludhogar.cl/pastillero"),
    dict(slug="barra-bano", name="Barra de baño de seguridad", category="home_safety", vendor="SaludHogar",
         price_clp=27990, sponsored=False, conditions=["Movilidad reducida", "Parkinson"],
         description="Barra de sujeción antideslizante para regadera o tina. Instalación con ventosas de fijación rápida.",
         external_url="https://saludhogar.cl/barra-bano"),
    dict(slug="monitor-signos-vitales", name="Monitor de signos vitales portátil", category="monitoring",
         vendor="OrtoChile", price_clp=69990, sponsored=False, conditions=["Hipertensión", "Diabetes"],
         description="Oxímetro y monitor de frecuencia cardíaca portátil, pantalla grande, fácil de leer.",
         external_url="https://ortochile.cl/monitor-vitales"),
    dict(slug="reloj-gps-sos", name="Reloj con GPS y botón SOS", category="monitoring", vendor="SaludHogar",
         price_clp=49990, sponsored=False, conditions=["Alzheimer", "Demencia"],
         description="Reloj de pulsera que comparte la ubicación con la familia y llama a un contacto "
                     "con un solo botón. Útil si tu familiar suele desorientarse.",
         external_url="https://saludhogar.cl/reloj-gps"),
]

FAMILY_REVIEW_NAMES = ["Familia Pérez", "Familia González", "Familia Rojas", "Familia Silva"]


async def seed() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_session_factory()() as db:
        for table in (models.ChatMessage, models.ChatConversation,
                      models.CaregiverEngagement, models.ContactRequest, models.CaregiverReview,
                     models.CaregiverDocument, models.CaregiverProfile, models.PatientMember,
                     models.Patient, models.ProductClick, models.MarketProduct, models.RefreshSession, models.User):
            await db.execute(delete(table))

        # ---- Productos ----
        for p in PRODUCTS:
            db.add(models.MarketProduct(
                id=product_id(p["slug"]), name=p["name"], category=p["category"], vendor=p["vendor"],
                description=p["description"], price_clp=p["price_clp"],
                price_range="$" + f"{p['price_clp']:,}".replace(",", "."), is_sponsored=p["sponsored"],
                conditions=p["conditions"], external_url=p["external_url"],
                thumbnail_url=f"{AVATAR_BASE}/demo/products/{p['slug']}.svg"))

        # ---- Cuidadoras ----
        for c in CAREGIVERS:
            user = models.User(full_name=c["full_name"], email=c["email"],
                               password_hash=hash_password("Cuidado123!"), account_type="caregiver",
                               avatar_url=f"{AVATAR_BASE}/demo/avatars/{c['slug']}.svg")
            db.add(user)
            await db.flush()
            profile = models.CaregiverProfile(
                user_id=user.id, headline=c["headline"], bio=f"Soy {c['full_name']}, cuidadora con vocación "
                "de servicio. Me dedico al cuidado de adultos mayores con paciencia, cariño y responsabilidad.",
                years_experience=c["years_experience"], specialties=c["specialties"],
                languages=c["languages"], zones=c["zones"], certifications=c["certifications"],
                is_listed=True, is_featured=c["featured"], admin_status="approved")
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
                                 conditions=["Movilidad reducida"],
                                 medication_allergies=["Penicilina"], food_allergies=["Mariscos"],
                                 notes="Le gusta la música y el jardín.")
        db.add(patient)
        await db.flush()
        db.add(models.PatientMember(patient_id=patient.id, user_id=family.id, role="family", is_owner=True))

        # ---- Trabajo activo demo: la familia ya contrató a María Torres ----
        maria = (await db.execute(select(models.CaregiverProfile)
                                  .join(models.User, models.User.id == models.CaregiverProfile.user_id)
                                  .where(models.User.email == "maria@cuidado.cl"))).scalar_one()
        db.add(models.CaregiverEngagement(caregiver_profile_id=maria.id, family_user_id=family.id,
                                          patient_id=patient.id))

        await db.commit()
        print(f"Seed completado: {len(CAREGIVERS)} cuidadoras publicadas, 1 familia demo, {len(PRODUCTS)} productos.")


if __name__ == "__main__":
    asyncio.run(seed())
