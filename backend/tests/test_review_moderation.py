"""Reseñas malas que restan puntos y moderación del staff (archivar, restaurar, eliminar)."""
import uuid

import pytest

from app import general_client
from app.errors import ApiError

INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
BASE = "/api/v1/admin/marketplace"


@pytest.fixture
def pushed(monkeypatch):
    calls = {"moderation": []}

    async def noop(*a, **k):
        return None

    async def moderation(email, action, **kw):
        calls["moderation"].append((email, action, kw))

    monkeypatch.setattr(general_client, "push_status", noop)
    monkeypatch.setattr(general_client, "push_document_review", noop)
    monkeypatch.setattr(general_client, "push_review_moderation", moderation)
    return calls


async def approved_caregiver(client, admin_headers, email):
    r = await client.post(f"{BASE}/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": email, "name": f"Cuidadora {email[:6]}", "email": email, "zone": "Ñuñoa",
        "specialties": [], "languages": ["Español"], "certifications_count": 0})
    cid = r.json()["caregiver_id"]
    for t in ("id_card", "background_check"):
        await client.post(f"{BASE}/documents/sync", headers=INTERNAL, json={
            "caregiver_email": email, "doc_type": t, "file_url": f"https://files/{t}.png",
            "original_filename": f"{t}.png", "is_change": False})
        await client.post(f"{BASE}/caregivers/{cid}/documents/{t}/review", headers=admin_headers,
                          json={"action": "approve"})
    # Para aprobar también hay que resolver el cobro de verificación (se exime para la prueba).
    await client.post(f"{BASE}/caregivers/{cid}/verification", headers=admin_headers, json={"action": "waived"})
    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 200, r.text
    return cid


async def add_review(client, headers, cid, rating, family="Familia Prueba"):
    r = await client.post(f"{BASE}/reviews", headers=headers,
                          json={"caregiver_id": cid, "family_name": family, "rating": rating, "comment": "x"})
    assert r.status_code == 201, r.text
    return r.json()


async def total_points(client, headers, cid):
    r = await client.get(f"{BASE}/caregivers/ranking?page_size=100", headers=headers)
    return next(i["points"] for i in r.json()["items"] if i["caregiver_id"] == cid)


@pytest.mark.parametrize("rating,awarded", [(5, 15), (4, 15), (3, 10), (2, 5), (1, -5)])
async def test_each_rating_adds_or_removes_points(client, admin_headers, pushed, rating, awarded):
    cid = await approved_caregiver(client, admin_headers, f"pts{rating}@test.cl")
    review = await add_review(client, admin_headers, cid, rating)
    assert review["points_awarded"] == awarded
    assert await total_points(client, admin_headers, cid) == awarded


async def test_bad_reviews_push_a_caregiver_down_the_ranking(client, admin_headers, pushed):
    good = await approved_caregiver(client, admin_headers, "buena@test.cl")
    bad = await approved_caregiver(client, admin_headers, "mala@test.cl")
    await add_review(client, admin_headers, good, 5)
    await add_review(client, admin_headers, bad, 1)
    await add_review(client, admin_headers, bad, 1, "Otra Familia")
    ranking = (await client.get(f"{BASE}/caregivers/ranking?page_size=100", headers=admin_headers)).json()["items"]
    order = [i["caregiver_id"] for i in ranking]
    assert order.index(good) < order.index(bad)
    assert await total_points(client, admin_headers, bad) == -10


async def test_archiving_a_review_undoes_its_effect_and_restoring_brings_it_back(client, admin_headers, pushed):
    email = "archivo@test.cl"
    cid = await approved_caregiver(client, admin_headers, email)
    await add_review(client, admin_headers, cid, 5)
    bad = await add_review(client, admin_headers, cid, 1, "Familia Enojada")
    assert await total_points(client, admin_headers, cid) == 10
    assert (await client.get(f"{BASE}/caregivers/{cid}", headers=admin_headers)).json()["rating_avg"] == 3.0

    r = await client.patch(f"{BASE}/reviews/{bad['id']}", headers=admin_headers, json={"archived": True})
    assert r.status_code == 200 and r.json()["archived_at"] is not None
    assert pushed["moderation"][-1][:2] == (email, "archive")
    assert await total_points(client, admin_headers, cid) == 15  # la reseña mala ya no resta
    d = (await client.get(f"{BASE}/caregivers/{cid}", headers=admin_headers)).json()
    assert d["rating_avg"] == 5.0 and d["reviews_count"] == 1

    # Sigue visible para el staff, marcada como archivada.
    items = (await client.get(f"{BASE}/caregivers/{cid}/reviews", headers=admin_headers)).json()["items"]
    assert len(items) == 2 and sum(1 for i in items if i["archived_at"]) == 1

    r = await client.patch(f"{BASE}/reviews/{bad['id']}", headers=admin_headers, json={"archived": False})
    assert r.status_code == 200 and r.json()["archived_at"] is None
    assert pushed["moderation"][-1][:2] == (email, "restore")
    assert await total_points(client, admin_headers, cid) == 10
    assert (await client.get(f"{BASE}/caregivers/{cid}", headers=admin_headers)).json()["reviews_count"] == 2


async def test_deleting_a_review_removes_it_and_its_points(client, admin_headers, analyst_headers, pushed):
    cid = await approved_caregiver(client, admin_headers, "borrar@test.cl")
    keep = await add_review(client, admin_headers, cid, 4)
    gone = await add_review(client, admin_headers, cid, 2, "Familia Injusta")
    assert await total_points(client, admin_headers, cid) == 20

    assert (await client.delete(f"{BASE}/reviews/{gone['id']}", headers=analyst_headers)).status_code == 403
    assert (await client.delete(f"{BASE}/reviews/{gone['id']}", headers=admin_headers)).status_code == 204
    assert pushed["moderation"][-1][1] == "delete"
    assert await total_points(client, admin_headers, cid) == 15
    items = (await client.get(f"{BASE}/caregivers/{cid}/reviews", headers=admin_headers)).json()["items"]
    assert [i["id"] for i in items] == [keep["id"]]
    assert (await client.delete(f"{BASE}/reviews/{gone['id']}", headers=admin_headers)).status_code == 404
    assert (await client.delete(f"{BASE}/reviews/{uuid.uuid4()}", headers=admin_headers)).status_code == 404


async def test_nothing_changes_if_the_site_cannot_be_told(client, admin_headers, pushed, monkeypatch):
    cid = await approved_caregiver(client, admin_headers, "falla@test.cl")
    review = await add_review(client, admin_headers, cid, 1)

    async def fails(*a, **k):
        raise ApiError(502, "GENERAL_SYNC_FAILED", "No se pudo avisar al sitio público.")

    monkeypatch.setattr(general_client, "push_review_moderation", fails)
    assert (await client.patch(f"{BASE}/reviews/{review['id']}", headers=admin_headers,
                               json={"archived": True})).status_code == 502
    assert (await client.delete(f"{BASE}/reviews/{review['id']}", headers=admin_headers)).status_code == 502
    items = (await client.get(f"{BASE}/caregivers/{cid}/reviews", headers=admin_headers)).json()["items"]
    assert len(items) == 1 and items[0]["archived_at"] is None


async def test_the_id_of_the_site_review_is_kept_to_moderate_it_later(client, admin_headers, pushed):
    email = "sitio@test.cl"
    cid = await approved_caregiver(client, admin_headers, email)
    site_id = str(uuid.uuid4())
    r = await client.post(f"{BASE}/reviews/sync", headers=INTERNAL, json={
        "caregiver_email": email, "family_name": "Familia Sitio", "rating": 2, "comment": "Llegó tarde",
        "review_id": site_id})
    assert r.status_code == 201 and r.json()["points_awarded"] == 5
    await client.patch(f"{BASE}/reviews/{r.json()['id']}", headers=admin_headers, json={"archived": True})
    assert pushed["moderation"][-1][2]["review_id"] == site_id
