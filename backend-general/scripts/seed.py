"""Seed de datos demo para la API general.

Uso: python -m scripts.seed
Credenciales demo:
    familia@demo.cl / Familia123!   (cuenta de familia, con un paciente creado)
    maria@cuidado.cl / Cuidado123!  (cuenta de cuidadora, publicada en el marketplace)
"""
import asyncio
import json
from pathlib import Path
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

# Las cuidadoras salen de demo_cuidadoras.json, la misma fuente que usa la Consola (backend/scripts/seed.py):
# así las dos aplicaciones muestran las mismas personas, reseñas y estado de pago.
CAREGIVERS = json.loads((Path(__file__).parent / "demo_cuidadoras.json").read_text(encoding="utf-8"))["caregivers"]

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
                     models.CaregiverDocument, models.ProfileView, models.CaregiverProfile, models.PatientMember,
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
                is_listed=True, admin_status=c["status"],
                # Misma regla que la Consola: solo quien pagó la verificación es «perfil calificado»; una exención
                # vigente la deja publicada hasta que venza.
                is_qualified=c["fee"]["status"] == "paid",
                listing_until=NOW + timedelta(days=c["fee"]["waiver_days"]) if c["fee"]["status"] == "waived" else None)
            db.add(profile)
            await db.flush()
            for rv in c["reviews"]:
                db.add(models.CaregiverReview(
                    caregiver_profile_id=profile.id,
                    author_user_id=user.id,  # placeholder: reseñas demo, no de un familiar real
                    author_name=rv["family"], rating=rv["rating"], comment=rv["comment"],
                    created_at=NOW - timedelta(days=rv["days_ago"])))
            if c["reviews"]:
                ratings = [rv["rating"] for rv in c["reviews"]]
                profile.rating_avg = round(sum(ratings) / len(ratings), 2)
                profile.reviews_count = len(ratings)

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

        # ---- Trabajo activo demo: la familia ya contrató a la cuidadora marcada como «engaged» ----
        for c in CAREGIVERS:
            if c["engaged"]:
                hired = (await db.execute(select(models.CaregiverProfile)
                                          .join(models.User, models.User.id == models.CaregiverProfile.user_id)
                                          .where(models.User.email == c["email"]))).scalar_one()
                db.add(models.CaregiverEngagement(caregiver_profile_id=hired.id, family_user_id=family.id,
                                                  patient_id=patient.id))

        # Visitas de ejemplo a las fichas (solo demo): los perfiles calificados reciben más.
        rng = random.Random(7)
        for profile in (await db.execute(select(models.CaregiverProfile)
                                         .where(models.CaregiverProfile.admin_status == "approved"))).scalars().all():
            for _ in range(rng.randint(28, 52) if profile.is_qualified else rng.randint(4, 14)):
                db.add(models.ProfileView(caregiver_profile_id=profile.id, viewer_user_id=family.id,
                                          created_at=NOW - timedelta(days=rng.randint(0, 28), hours=rng.randint(0, 23))))

        await db.commit()
        published = sum(1 for c in CAREGIVERS if c["status"] == "approved")
        print(f"Seed completado: {published} cuidadoras publicadas ({len(CAREGIVERS) - published} pendiente), 1 familia demo, {len(PRODUCTS)} productos.")


if __name__ == "__main__":
    asyncio.run(seed())
