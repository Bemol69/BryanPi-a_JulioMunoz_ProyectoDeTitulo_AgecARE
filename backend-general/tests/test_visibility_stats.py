"""Filtro de perfiles calificados y estadísticas de visibilidad de la cuidadora."""
from tests.conftest import login

API = "/api/v1"


async def search(client, headers, **params):
    r = await client.get(f"{API}/marketplace/caregivers", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def stats(client, headers):
    r = await client.get(f"{API}/caregiver/stats", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Filtro "solo perfiles calificados" ----------
async def test_families_can_filter_to_qualified_profiles_only(client, family):
    everyone = await search(client, family)
    qualified = await search(client, family, qualified_only=True)
    assert 0 < len(qualified) < len(everyone)
    assert all(c["is_qualified"] for c in qualified)
    assert {c["full_name"] for c in qualified} == {"María Torres", "Javiera Soto", "Rocío Álvarez", "Sebastián Rivas"}


# ---------- Visitas y contactos ----------
async def test_opening_a_profile_counts_one_visit_even_if_repeated(client, family):
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    before = (await stats(client, javiera))["views_30d"]
    pid = next(c for c in await search(client, family) if c["full_name"] == "Javiera Soto")["profile_id"]
    for _ in range(3):
        assert (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).status_code == 200
    assert (await stats(client, javiera))["views_30d"] == before + 1  # tres aperturas seguidas = una visita


async def test_different_families_add_up_and_the_search_alone_is_not_a_visit(client, family):
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    before = (await stats(client, javiera))["views_30d"]
    await search(client, family)  # solo mirar la lista no cuenta
    assert (await stats(client, javiera))["views_30d"] == before

    other = await login(client, "familia@demo.cl", "Familia123!")
    reg = await client.post(f"{API}/auth/register", json={
        "full_name": "Otra Familia", "email": "visita@familia.cl", "password": "Familia123!", "account_type": "family"})
    other2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    pid = next(c for c in await search(client, family) if c["full_name"] == "Javiera Soto")["profile_id"]
    await client.get(f"{API}/marketplace/caregivers/{pid}", headers=other)
    await client.get(f"{API}/marketplace/caregivers/{pid}", headers=other2)
    assert (await stats(client, javiera))["views_30d"] == before + 2


async def test_families_that_contacted_her_are_counted_once_each(client, family):
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    pid = next(c for c in await search(client, family) if c["full_name"] == "Javiera Soto")["profile_id"]
    assert (await stats(client, javiera))["families_contacted_30d"] == 0
    # La misma familia le escribe dos veces: sigue siendo una familia.
    for _ in range(2):
        r = await client.post(f"{API}/marketplace/caregivers/{pid}/contact", json={"message": "Hola"}, headers=family)
        assert r.status_code in (200, 201), r.text
    assert (await stats(client, javiera))["families_contacted_30d"] == 1
    # Otra familia distinta suma una más.
    reg = await client.post(f"{API}/auth/register", json={
        "full_name": "Otra Familia", "email": "contacto@familia.cl", "password": "Familia123!", "account_type": "family"})
    other = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assert (await client.post(f"{API}/marketplace/caregivers/{pid}/contact", json={"message": "Hola"}, headers=other)).status_code in (200, 201)
    assert (await stats(client, javiera))["families_contacted_30d"] == 2


async def test_stats_compare_with_the_platform_average(client):
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    s = await stats(client, javiera)
    assert s["is_qualified"] is True
    # El seed da más visitas a los calificados: el promedio de ellos supera al de los demás.
    assert s["avg_views_qualified"] > s["avg_views_unqualified"] > 0
    assert s["views_30d"] > 0


async def test_only_caregivers_have_stats(client, family):
    assert (await client.get(f"{API}/caregiver/stats", headers=family)).status_code == 403
