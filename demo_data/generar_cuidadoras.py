"""Genera la fuente única de los datos de demostración de las cuidadoras.

El sitio (backend-general) y la Consola (backend) tienen su propio `scripts/seed.py`. Antes cada uno traía su
propia lista de cuidadoras y reseñas, así que no coincidían (una cuidadora con 4,7 estrellas en el sitio y sin
reseñas en la Consola, otra que solo existía en uno). Ahora los dos leen el mismo archivo.

Uso (desde la raíz del repo):  python demo_data/generar_cuidadoras.py
Escribe demo_data/cuidadoras.json y una copia en cada backend (los seeds corren dentro de Docker, que solo ve su carpeta).
Hay una prueba en cada backend que falla si las copias dejan de ser idénticas.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(20260909)

FAMILIES = ["Familia Pérez", "Familia González", "Familia Rojas", "Familia Silva",
            "Familia Contreras", "Familia Herrera", "Familia Muñoz", "Familia Castro"]
GOOD = ["Muy puntual y cariñosa con mi papá.", "Excelente manejo de emergencias.",
        "Se nota la experiencia, muy profesional.", "Mi mamá quedó feliz, la recomiendo.",
        "Comunicación clara y constante durante el turno."]
OK = ["Buen trabajo en general, llegó unos minutos tarde.", "Cumplió lo básico, esperaba más iniciativa."]


def reviews(ratings):
    out = []
    for i, rating in enumerate(ratings):
        out.append({"rating": rating, "family": rng.choice(FAMILIES),
                    "comment": rng.choice(GOOD if rating >= 4 else OK),
                    "days_ago": rng.randint(1, 58), "job": f"TRB-2026{i + 1:04d}"})
    return out


PAID = lambda days: {"status": "paid", "paid_days_ago": days, "method": "transfer"}

CAREGIVERS = [
    dict(slug="maria", full_name="María Torres", email="maria@cuidado.cl", status="approved", engaged=True,
         headline="Cuidadora certificada · 8 años de experiencia", years_experience=8,
         specialties=["Alzheimer", "Movilidad reducida", "Posoperatorio"], languages=["Español"],
         zones=["Providencia", "Ñuñoa"],
         certifications=[{"name": "Cuidados geriátricos", "issuer": "INACAP", "year": 2019}],
         fee=PAID(3), reviews=reviews([5] * 12 + [4] * 5 + [3])),  # promedio 4,61: «Destacada»
    dict(slug="javiera", full_name="Javiera Soto", email="javiera@cuidado.cl", status="approved", engaged=False,
         headline="Enfermera geriátrica · turnos nocturnos", years_experience=6,
         specialties=["Cuidados paliativos", "Control de medicación"], languages=["Español", "Inglés"],
         zones=["Las Condes"],
         certifications=[{"name": "Enfermería geriátrica", "issuer": "U. de Chile", "year": 2020}],
         fee=PAID(7), reviews=reviews([5] * 15 + [4] * 8 + [3])),  # promedio 4,58: «Destacada»
    dict(slug="rocio", full_name="Rocío Álvarez", email="rocio@cuidado.cl", status="approved", engaged=False,
         headline="Acompañamiento y estimulación cognitiva", years_experience=4,
         specialties=["Estimulación cognitiva", "Acompañamiento"], languages=["Español"], zones=["Maipú"],
         certifications=[], fee=PAID(11), reviews=reviews([5, 5])),  # 5,0 pero con solo 2 reseñas: aún no es «Destacada»
    dict(slug="fernanda", full_name="Fernanda Ibáñez", email="fernanda@cuidado.cl", status="approved", engaged=False,
         headline="Cuidadora de día, experiencia con Alzheimer", years_experience=5,
         specialties=["Alzheimer"], languages=["Español"], zones=["Providencia"],
         # Aprobada antes del cobro y sin pagar: se ve en las búsquedas pero sin insignia «calificado».
         certifications=[], fee={"status": "unpaid"}, reviews=reviews([4, 5, 5, 3, 5])),
    dict(slug="sebastian", full_name="Sebastián Rivas", email="sebastian@cuidado.cl", status="approved", engaged=False,
         headline="Técnico en enfermería · turnos de día", years_experience=7,
         specialties=["Movilidad reducida", "Posoperatorio", "Control de medicación"], languages=["Español"],
         zones=["Santiago Centro", "Estación Central"],
         certifications=[{"name": "Técnico en enfermería", "issuer": "Duoc UC", "year": 2018}],
         fee=PAID(19), reviews=reviews([5, 4, 5, 5, 4, 5])),
    dict(slug="andres", full_name="Andrés Pizarro", email="andres@cuidado.cl", status="approved", engaged=False,
         headline="Cuidador con experiencia en demencia y acompañamiento", years_experience=10,
         specialties=["Demencia", "Acompañamiento"], languages=["Español"], zones=["La Florida", "Puente Alto"],
         certifications=[],
         fee={"status": "waived", "waiver_reason": "launch_promo", "waiver_note": "Cuidador piloto del lanzamiento.",
              "waiver_days": 60},
         reviews=reviews([5, 5, 4])),
    # Postulación nueva: todavía sin aprobar ni pagar. Existe en las dos aplicaciones pero no aparece en las búsquedas.
    dict(slug="paula", full_name="Paula Fuentes", email="paula@cuidado.cl", status="pending", engaged=False,
         headline="Técnica en cuidados · posoperatorio", years_experience=3,
         specialties=["Posoperatorio"], languages=["Español", "Inglés"], zones=["Ñuñoa"],
         certifications=[], fee={"status": "unpaid"}, reviews=[]),
]

text = json.dumps({"caregivers": CAREGIVERS}, ensure_ascii=False, indent=1) + "\n"
for target in (ROOT / "demo_data", ROOT / "backend" / "scripts", ROOT / "backend-general" / "scripts"):
    (target / "demo_cuidadoras.json").write_text(text, encoding="utf-8", newline="\n")
print("listo:", {c["slug"]: len(c["reviews"]) for c in CAREGIVERS})
