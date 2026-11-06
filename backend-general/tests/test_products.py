"""Rentabilidad: artículos de apoyo (orden, recomendación, clics, catálogo de la Consola) y verificación."""
from uuid import uuid4

from tests.conftest import INTERNAL

API = "/api/v1"
ANDADERA = "Andadera plegable con ruedas"


async def products(client, headers, **params):
    r = await client.get(f"{API}/marketplace/products", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()["items"]


# ---------- Orden y recomendación ----------
async def test_products_recommended_for_a_relative_come_first(client, family):
    items = await products(client, family)
    assert len(items) == 6
    # Elena (la adulta mayor demo) tiene "Movilidad reducida": sus productos van primero.
    recommended = [i for i in items if i["recommended_for"]]
    assert {i["name"] for i in recommended} == {ANDADERA, "Bastón ortopédico de 4 puntas", "Barra de baño de seguridad"}
    assert [i["recommended_for"] is not None for i in items] == [True] * 3 + [False] * 3
    assert items[0]["name"] == ANDADERA  # recomendado y además patrocinado
    assert items[0]["recommended_for"] == "Elena Muñoz · Movilidad reducida"


async def test_sponsored_products_lead_when_there_is_no_match(client, maria):
    items = await products(client, maria)  # una cuenta sin familiares: nada que recomendar
    assert all(i["recommended_for"] is None for i in items)
    assert items[0]["name"] == ANDADERA and items[0]["is_sponsored"] is True
    assert sum(1 for i in items if i["is_sponsored"]) == 1


async def test_product_cards_show_vendor_and_price_in_pesos(client, family):
    andadera = next(i for i in await products(client, family) if i["name"] == ANDADERA)
    assert andadera["vendor"] == "OrtoChile" and andadera["price_clp"] == 54990
    assert andadera["price_range"] == "$54.990"


async def test_products_can_be_filtered_by_category_and_search(client, family):
    mobility = await products(client, family, category="mobility")
    assert {i["name"] for i in mobility} == {ANDADERA, "Bastón ortopédico de 4 puntas"}
    found = await products(client, family, q="gps")
    assert [i["name"] for i in found] == ["Reloj con GPS y botón SOS"]
    assert await products(client, family, q="saludhogar")  # también busca por proveedor


# ---------- Clics ----------
async def test_click_is_recorded_once_per_burst(client, family):
    pid = next(i for i in await products(client, family) if i["name"] == ANDADERA)["product_id"]
    for _ in range(3):
        assert (await client.post(f"{API}/marketplace/products/{pid}/click", headers=family)).status_code == 204

    stats = (await client.get(f"{API}/internal/products/stats", headers=INTERNAL)).json()["items"]
    mine = next(i for i in stats if i["product_id"] == pid)
    assert mine["clicks_total"] == 1 and mine["clicks_30d"] == 1  # tres clics seguidos cuentan uno


async def test_clicks_from_different_people_add_up(client, family, maria):
    pid = next(i for i in await products(client, family) if i["name"] == ANDADERA)["product_id"]
    await client.post(f"{API}/marketplace/products/{pid}/click", headers=family)
    await client.post(f"{API}/marketplace/products/{pid}/click", headers=maria)
    stats = (await client.get(f"{API}/internal/products/stats", headers=INTERNAL)).json()["items"]
    assert next(i for i in stats if i["product_id"] == pid)["clicks_total"] == 2


async def test_click_on_an_unknown_product_is_a_404(client, family):
    r = await client.post(f"{API}/marketplace/products/{uuid4()}/click", headers=family)
    assert r.status_code == 404


# ---------- Catálogo administrado desde la Consola ----------
def payload(**over):
    base = {"id": str(uuid4()), "name": "Silla de ducha plegable", "category": "home_safety",
            "vendor": "SaludHogar", "description": "Con respaldo antideslizante.", "price_clp": 32990,
            "external_url": "https://saludhogar.cl/silla-ducha", "image_url": None,
            "is_sponsored": True, "conditions": ["Parkinson"], "is_active": True}
    base.update(over)
    return base


async def test_internal_product_endpoints_require_the_shared_key(client):
    assert (await client.post(f"{API}/internal/products", json=payload())).status_code == 401
    assert (await client.get(f"{API}/internal/products/stats")).status_code == 401


async def test_console_creates_updates_and_hides_a_product(client, family):
    body = payload()
    assert (await client.post(f"{API}/internal/products", json=body, headers=INTERNAL)).status_code == 204
    items = await products(client, family)
    assert len(items) == 7
    created = next(i for i in items if i["product_id"] == body["id"])
    assert created["price_range"] == "$32.990" and created["is_sponsored"] is True

    body.update(price_clp=29990, is_sponsored=False)
    assert (await client.post(f"{API}/internal/products", json=body, headers=INTERNAL)).status_code == 204
    updated = next(i for i in await products(client, family) if i["product_id"] == body["id"])
    assert updated["price_clp"] == 29990 and updated["is_sponsored"] is False

    body.update(is_active=False)  # archivado en la Consola
    await client.post(f"{API}/internal/products", json=body, headers=INTERNAL)
    assert len(await products(client, family)) == 6
    assert (await client.get(f"{API}/marketplace/products/{body['id']}", headers=family)).status_code == 404
    assert (await client.post(f"{API}/marketplace/products/{body['id']}/click", headers=family)).status_code == 404


async def test_new_product_is_recommended_when_a_relative_has_that_condition(client, family):
    body = payload(conditions=["Movilidad reducida"], is_sponsored=False)
    await client.post(f"{API}/internal/products", json=body, headers=INTERNAL)
    created = next(i for i in await products(client, family) if i["product_id"] == body["id"])
    assert created["recommended_for"] == "Elena Muñoz · Movilidad reducida"


async def test_unknown_category_is_rejected(client):
    r = await client.post(f"{API}/internal/products", json=payload(category="juguetes"), headers=INTERNAL)
    assert r.status_code == 422


# ---------- Verificación de la cuidadora ----------
async def test_caregiver_sees_her_verification_payment_state(client, maria, monkeypatch):
    import app.routers.caregiver as caregiver_router

    async def fake(email):
        return {"fee_clp": 9990, "status": "unpaid", "reference": "AC-1A2B3C", "paid_at": None}

    monkeypatch.setattr(caregiver_router, "fetch_admin_verification", fake)
    r = await client.get(f"{API}/caregiver/verification", headers=maria)
    assert r.status_code == 200, r.text
    assert r.json() == {"available": True, "fee_clp": 9990, "status": "unpaid", "reference": "AC-1A2B3C",
                        "paid_at": None, "payment_info": ""}


async def test_verification_state_is_hidden_when_the_console_does_not_answer(client, maria, monkeypatch):
    import app.routers.caregiver as caregiver_router

    async def down(email):
        return None

    monkeypatch.setattr(caregiver_router, "fetch_admin_verification", down)
    r = await client.get(f"{API}/caregiver/verification", headers=maria)
    assert r.status_code == 200 and r.json()["available"] is False


async def test_only_caregivers_have_a_verification(client, family):
    assert (await client.get(f"{API}/caregiver/verification", headers=family)).status_code == 403
