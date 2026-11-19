"""Los datos de demostración del sitio y de la Consola salen del mismo archivo y deben coincidir."""
import json
from pathlib import Path

from sqlalchemy import func, select

import app.database as database
from app import models

HERE = Path(__file__).resolve().parents[1] / "scripts" / "demo_cuidadoras.json"
OTHER = Path(__file__).resolve().parents[2] / "backend" / "scripts" / "demo_cuidadoras.json"
DEMO = json.loads(HERE.read_text(encoding="utf-8"))["caregivers"]


def test_both_apps_carry_the_same_demo_file():
    if not OTHER.exists():
        return
    assert HERE.read_bytes() == OTHER.read_bytes(), "demo_cuidadoras.json difiere entre backend y backend-general"


async def test_site_seed_matches_the_shared_demo_file(client):
    async with database.get_session_factory()() as db:
        profiles = (await db.execute(select(models.CaregiverProfile, models.User)
                                     .join(models.User, models.User.id == models.CaregiverProfile.user_id))).all()
        by_email = {u.email: (p, u) for p, u in profiles}
        assert set(by_email) == {d["email"] for d in DEMO}, "el sitio tiene cuidadoras que el archivo no define (o le faltan)"
        for d in DEMO:
            p, u = by_email[d["email"]]
            assert u.full_name == d["full_name"] and p.admin_status == d["status"]
            assert p.zones == d["zones"] and set(p.languages) == set(d["languages"])
            # Misma regla que la Consola: solo quien pagó es «calificado»; la exención no da insignia.
            assert p.is_qualified == (d["fee"]["status"] == "paid"), d["full_name"]
            n = (await db.execute(select(func.count(models.CaregiverReview.id))
                                  .where(models.CaregiverReview.caregiver_profile_id == p.id))).scalar_one()
            assert n == len(d["reviews"]) == p.reviews_count, d["full_name"]
            if d["reviews"]:
                assert p.rating_avg == round(sum(r["rating"] for r in d["reviews"]) / len(d["reviews"]), 2)
        engaged = {d["email"] for d in DEMO if d["engaged"]}
        working = {u.email for p, u in profiles
                   if (await db.execute(select(models.CaregiverEngagement.id).where(
                       models.CaregiverEngagement.caregiver_profile_id == p.id,
                       models.CaregiverEngagement.status == "active"))).first() is not None}
        assert working == engaged


async def test_pending_demo_caregiver_is_not_visible_to_families(client, family):
    pending = [d["full_name"] for d in DEMO if d["status"] != "approved"]
    r = await client.get("/api/v1/marketplace/caregivers?page_size=100", headers=family)
    names = {c["full_name"] for c in r.json()["items"]}
    assert pending and not names & set(pending)
    assert names == {d["full_name"] for d in DEMO if d["status"] == "approved"}
