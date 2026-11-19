"""Reseñas que el staff registra en la Consola: se publican en el sitio y cuentan para la valoración y para «Destacada»."""
from uuid import uuid4

from tests.conftest import INTERNAL, login

API = "/api/v1"


async def search(client, headers):
    r = await client.get(f"{API}/marketplace/caregivers", headers=headers)
    assert r.status_code == 200, r.text
    return {c["full_name"]: c for c in r.json()["items"]}


async def push(client, email="rocio@cuidado.cl", rating=5, review_id=None, family="Familia Prueba", comment="Excelente"):
    return await client.post(f"{API}/internal/reviews", headers=INTERNAL, json={
        "email": email, "review_id": str(review_id or uuid4()), "family_name": family, "rating": rating, "comment": comment})


async def test_a_console_review_shows_up_on_the_site_and_updates_the_rating(client, family):
    before = (await search(client, family))["Rocío Álvarez"]
    assert before["reviews_count"] == 2
    assert (await push(client, rating=4)).status_code == 204
    after = (await search(client, family))["Rocío Álvarez"]
    assert after["reviews_count"] == 3
    assert after["rating_avg"] == round((5 + 5 + 4) / 3, 2)

    rocio = await login(client, "rocio@cuidado.cl", "Cuidado123!")
    mine = (await client.get(f"{API}/caregiver/reviews", headers=rocio)).json()
    assert any(r["author_name"] == "Familia Prueba" and r["rating"] == 4 for r in mine)


async def test_three_console_reviews_make_a_qualified_caregiver_featured(client, family):
    # Rocío es calificada con 5,0 pero tiene 2 reseñas: todavía no es Destacada.
    assert not (await search(client, family))["Rocío Álvarez"]["is_featured"]
    assert (await push(client, rating=5)).status_code == 204
    assert (await search(client, family))["Rocío Álvarez"]["is_featured"]  # 3 reseñas, 5,0 y calificada


async def test_reviews_do_not_make_an_unqualified_caregiver_featured(client, family):
    # Fernanda no pagó la verificación: con buenas reseñas sigue sin ser Destacada (falta ser calificada).
    start = (await search(client, family))["Fernanda Ibáñez"]["reviews_count"]
    for _ in range(3):
        assert (await push(client, email="fernanda@cuidado.cl", rating=5)).status_code == 204
    fernanda = (await search(client, family))["Fernanda Ibáñez"]
    assert fernanda["reviews_count"] == start + 3 and not fernanda["is_featured"]
    await client.post(f"{API}/internal/caregivers/qualified", headers=INTERNAL,
                      json={"email": "fernanda@cuidado.cl", "qualified": True})
    assert (await search(client, family))["Fernanda Ibáñez"]["is_featured"]


async def test_the_same_notice_twice_does_not_duplicate_the_review(client, family):
    rid = uuid4()
    await push(client, review_id=rid)
    await push(client, review_id=rid)
    assert (await search(client, family))["Rocío Álvarez"]["reviews_count"] == 3


async def test_archiving_it_from_the_console_removes_it_from_the_site(client, family):
    rid = uuid4()
    await push(client, review_id=rid, rating=1)
    assert (await search(client, family))["Rocío Álvarez"]["reviews_count"] == 3
    r = await client.post(f"{API}/internal/reviews/moderate", headers=INTERNAL, json={
        "email": "rocio@cuidado.cl", "action": "archive", "review_id": str(rid)})
    assert r.status_code == 204
    after = (await search(client, family))["Rocío Álvarez"]
    assert after["reviews_count"] == 2 and after["rating_avg"] == 5.0


async def test_the_endpoint_needs_the_key_and_a_known_caregiver(client):
    r = await client.post(f"{API}/internal/reviews", json={
        "email": "rocio@cuidado.cl", "review_id": str(uuid4()), "family_name": "X", "rating": 5})
    assert r.status_code == 401
    assert (await push(client, email="nadie@cuidado.cl")).status_code == 404
    assert (await push(client, rating=7)).status_code == 422
