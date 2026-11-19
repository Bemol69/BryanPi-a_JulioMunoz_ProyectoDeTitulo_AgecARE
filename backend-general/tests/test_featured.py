"""Destacada: calificada + valoración 4,5 o más + al menos 3 reseñas. Se calcula sola, no se marca a mano."""
from sqlalchemy import update

import app.database as database
from app import models
from tests.conftest import INTERNAL

API = "/api/v1"


async def search(client, headers):
    r = await client.get(f"{API}/marketplace/caregivers", headers=headers)
    assert r.status_code == 200, r.text
    return {c["full_name"]: c for c in r.json()["items"]}


async def change(email, **values):
    async with database.get_session_factory()() as db:
        from sqlalchemy import select
        user = (await db.execute(select(models.User).where(models.User.email == email))).scalar_one()
        await db.execute(update(models.CaregiverProfile).where(models.CaregiverProfile.user_id == user.id).values(**values))
        await db.commit()


async def test_featured_follows_the_rule_not_a_manual_flag(client, family):
    items = await search(client, family)
    featured = {name for name, c in items.items() if c["is_featured"]}
    # María, Javiera y Sebastián: calificados, valoración >= 4,5 y 3 o más reseñas.
    assert featured == {"María Torres", "Javiera Soto", "Sebastián Rivas"}
    assert not items["Rocío Álvarez"]["is_featured"]  # 5,0 pero solo 2 reseñas
    assert not items["Andrés Pizarro"]["is_featured"]  # buena valoración, pero está eximido (no calificado)
    assert not items["Fernanda Ibáñez"]["is_featured"]  # tampoco pagó


async def test_enough_reviews_make_a_qualified_profile_featured(client, family):
    assert not (await search(client, family))["Rocío Álvarez"]["is_featured"]
    await change("rocio@cuidado.cl", reviews_count=3)
    assert (await search(client, family))["Rocío Álvarez"]["is_featured"]


async def test_a_lower_rating_removes_the_mark(client, family):
    assert (await search(client, family))["Javiera Soto"]["is_featured"]
    await change("javiera@cuidado.cl", rating_avg=4.4)
    assert not (await search(client, family))["Javiera Soto"]["is_featured"]
    await change("javiera@cuidado.cl", rating_avg=4.5)  # el límite inclusive
    assert (await search(client, family))["Javiera Soto"]["is_featured"]


async def test_losing_the_qualified_badge_removes_the_mark(client, family):
    r = await client.post(f"{API}/internal/caregivers/qualified", headers=INTERNAL,
                          json={"email": "javiera@cuidado.cl", "qualified": False})
    assert r.status_code == 204
    assert not (await search(client, family))["Javiera Soto"]["is_featured"]


async def test_paying_is_what_lets_a_well_rated_profile_become_featured(client, family):
    # Andrés tiene 4,7 con 3 reseñas pero está eximido: al pagar, pasa a ser Destacado.
    assert not (await search(client, family))["Andrés Pizarro"]["is_featured"]
    await client.post(f"{API}/internal/caregivers/qualified", headers=INTERNAL,
                      json={"email": "andres@cuidado.cl", "qualified": True})
    assert (await search(client, family))["Andrés Pizarro"]["is_featured"]


async def test_featured_goes_first_among_available_qualified_profiles(client, family):
    items = list((await search(client, family)).values())
    available_qualified = [c for c in items if c["is_qualified"] and not c["is_engaged"]]
    flags = [c["is_featured"] for c in available_qualified]
    assert flags == sorted(flags, reverse=True)


async def test_the_profile_page_and_my_profile_agree(client, family):
    items = await search(client, family)
    maria = items["María Torres"]
    r = await client.get(f"{API}/marketplace/caregivers/{maria['profile_id']}", headers=family)
    assert r.json()["is_featured"] is True
    from tests.conftest import login
    me = await login(client, "maria@cuidado.cl", "Cuidado123!")
    assert (await client.get(f"{API}/caregiver/profile", headers=me)).json()["is_featured"] is True
    rocio = await login(client, "rocio@cuidado.cl", "Cuidado123!")
    assert (await client.get(f"{API}/caregiver/profile", headers=rocio)).json()["is_featured"] is False
