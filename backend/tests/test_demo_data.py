"""Los datos de demostración de la Consola y del sitio público salen del mismo archivo y deben coincidir."""
import json
from pathlib import Path

from sqlalchemy import func, select

import app.database as database
from app import models

HERE = Path(__file__).resolve().parents[1] / "scripts" / "demo_cuidadoras.json"
OTHER = Path(__file__).resolve().parents[2] / "backend-general" / "scripts" / "demo_cuidadoras.json"
DEMO = json.loads(HERE.read_text(encoding="utf-8"))["caregivers"]


def test_both_apps_carry_the_same_demo_file():
    """Se edita demo_data/generar_cuidadoras.py y se regenera: nunca a mano en un solo lado."""
    if not OTHER.exists():  # CI que solo trae una carpeta
        return
    assert HERE.read_bytes() == OTHER.read_bytes(), "demo_cuidadoras.json difiere entre backend y backend-general"
    root = Path(__file__).resolve().parents[2] / "demo_data" / "cuidadoras.json"
    assert not root.exists() or root.read_bytes() == HERE.read_bytes()


async def test_console_seed_matches_the_shared_demo_file(seeded):
    async with database.get_session_factory()() as db:
        rows = {c.email: c for c in (await db.execute(select(models.CaregiverProfile))).scalars().all()}
        for d in DEMO:
            c = rows[d["email"]]
            assert c.name == d["full_name"] and c.status == d["status"]
            assert c.zone == d["zones"][0]
            assert set(c.languages) == set(d["languages"]) and set(c.specialties) == set(d["specialties"])
            assert c.is_engaged == d["engaged"] and c.verification_fee_status == d["fee"]["status"]
            n = (await db.execute(select(func.count(models.CaregiverReview.id))
                                  .where(models.CaregiverReview.caregiver_id == c.id))).scalar_one()
            assert n == len(d["reviews"]) == c.reviews_count, d["full_name"]
            if d["reviews"]:
                avg = round(sum(r["rating"] for r in d["reviews"]) / len(d["reviews"]), 2)
                assert c.rating_avg == avg, d["full_name"]
            else:
                assert c.rating_avg is None
        assert {d["email"] for d in DEMO} <= set(rows), "a la Consola le faltan cuidadoras del archivo"
