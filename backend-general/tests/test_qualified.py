"""Perfil calificado: la cuidadora que pagó su verificación muestra la insignia y sale primero."""
from tests.conftest import INTERNAL

API = "/api/v1"
QUALIFIED = {"María Torres", "Javiera Soto", "Rocío Álvarez", "Sebastián Rivas"}


async def search(client, headers):
    r = await client.get(f"{API}/marketplace/caregivers", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def set_qualified(client, email, qualified):
    return await client.post(f"{API}/internal/caregivers/qualified", headers=INTERNAL,
                             json={"email": email, "qualified": qualified})


async def test_only_those_who_paid_are_qualified_and_they_come_first(client, family):
    items = await search(client, family)
    assert {c["full_name"] for c in items if c["is_qualified"]} == QUALIFIED
    flags = [c["is_qualified"] for c in items]
    assert flags == sorted(flags, reverse=True)  # todas las calificadas antes que el resto
    assert [c["full_name"] for c in items[len(QUALIFIED):]] and not any(flags[len(QUALIFIED):])


async def test_a_qualified_caregiver_who_is_working_still_goes_before_unqualified_ones(client, family):
    items = await search(client, family)
    maria = next(c for c in items if c["full_name"] == "María Torres")
    assert maria["is_engaged"] and maria["is_qualified"]
    unqualified_positions = [i for i, c in enumerate(items) if not c["is_qualified"]]
    assert items.index(maria) < min(unqualified_positions)


async def test_console_marks_and_unmarks_the_profile_as_qualified(client, family):
    # Andrés está eximido: sin insignia ni prioridad.
    assert not next(c for c in await search(client, family) if c["full_name"] == "Andrés Pizarro")["is_qualified"]

    assert (await set_qualified(client, "andres@cuidado.cl", True)).status_code == 204
    items = await search(client, family)
    andres = next(c for c in items if c["full_name"] == "Andrés Pizarro")
    assert andres["is_qualified"] is True
    assert items.index(andres) < min(i for i, c in enumerate(items) if not c["is_qualified"])

    assert (await set_qualified(client, "andres@cuidado.cl", False)).status_code == 204
    assert not next(c for c in await search(client, family) if c["full_name"] == "Andrés Pizarro")["is_qualified"]


async def test_qualified_badge_also_shows_on_the_profile_page(client, family):
    items = await search(client, family)
    javiera = next(c for c in items if c["full_name"] == "Javiera Soto")
    andres = next(c for c in items if c["full_name"] == "Andrés Pizarro")
    r = await client.get(f"{API}/marketplace/caregivers/{javiera['profile_id']}", headers=family)
    assert r.json()["is_qualified"] is True
    r = await client.get(f"{API}/marketplace/caregivers/{andres['profile_id']}", headers=family)
    assert r.json()["is_qualified"] is False


async def test_qualified_endpoint_needs_the_shared_key_and_a_known_caregiver(client):
    r = await client.post(f"{API}/internal/caregivers/qualified", json={"email": "andres@cuidado.cl", "qualified": True})
    assert r.status_code == 401
    assert (await set_qualified(client, "nadie@cuidado.cl", True)).status_code == 404


# ---------- Exención con vencimiento: al vencer, el perfil deja de mostrarse ----------
from datetime import datetime, timedelta, timezone  # noqa: E402


async def set_until(client, email, until, qualified=False):
    r = await client.post(f"{API}/internal/caregivers/qualified", headers=INTERNAL, json={
        "email": email, "qualified": qualified, "listing_until": until.isoformat() if until else None})
    assert r.status_code == 204, r.text


async def test_a_profile_whose_waiver_expired_is_hidden_until_it_pays(client, family):
    items = await search(client, family)
    andres = next(c for c in items if c["full_name"] == "Andrés Pizarro")  # el seed lo deja con 60 días de exención
    pid = andres["profile_id"]

    await set_until(client, "andres@cuidado.cl", datetime.now(timezone.utc) - timedelta(days=1))
    assert "Andrés Pizarro" not in {c["full_name"] for c in await search(client, family)}
    assert (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).status_code == 404
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/hire-requests", json={}, headers=family)
    assert r.status_code == 404

    # Paga: vuelve a mostrarse, ahora como perfil calificado.
    await set_until(client, "andres@cuidado.cl", None, qualified=True)
    shown = next(c for c in await search(client, family) if c["full_name"] == "Andrés Pizarro")
    assert shown["is_qualified"] is True


async def test_a_waiver_that_has_not_expired_keeps_the_profile_visible(client, family):
    await set_until(client, "andres@cuidado.cl", datetime.now(timezone.utc) + timedelta(days=3))
    assert "Andrés Pizarro" in {c["full_name"] for c in await search(client, family)}
    await set_until(client, "andres@cuidado.cl", None)  # exención sin vencimiento
    assert "Andrés Pizarro" in {c["full_name"] for c in await search(client, family)}
