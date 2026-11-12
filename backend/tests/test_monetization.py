"""Rentabilidad: cobro de verificación a cuidadoras y catálogo de artículos de apoyo."""
import pytest

from app import general_client

INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
BASE = "/api/v1/admin/marketplace"
EMAIL = "cobro.cuidadora@test.cl"


@pytest.fixture
def pushed(monkeypatch):
    """Registra los avisos al sitio público (estado y productos) en vez de hacer llamadas de red."""
    calls = {"status": [], "products": []}

    async def push_status(email, status):
        calls["status"].append((email, status))

    async def push_product(payload):
        calls["products"].append(payload)

    async def fetch_product_stats():
        return STATS

    async def push_document_review(email, doc_type, action, note):
        return None

    monkeypatch.setattr(general_client, "push_status", push_status)
    monkeypatch.setattr(general_client, "push_document_review", push_document_review)
    monkeypatch.setattr(general_client, "push_product", push_product)
    monkeypatch.setattr(general_client, "fetch_product_stats", fetch_product_stats)
    return calls


STATS: dict = {}


async def new_caregiver(client):
    r = await client.post(f"{BASE}/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": "u-cobro", "name": "Cuidadora Cobro", "email": EMAIL, "zone": "Ñuñoa",
        "specialties": [], "languages": [], "certifications_count": 0})
    assert r.status_code in (200, 201), r.text
    return r.json()["caregiver_id"]


async def test_new_caregiver_starts_unpaid_with_a_payment_reference(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    r = await client.get(f"{BASE}/caregivers/{cid}", headers=admin_headers)
    d = r.json()
    assert d["verification_fee_status"] == "unpaid" and d["verification_fee_clp"] == 9990
    assert d["verification_reference"].startswith("AC-")


async def test_site_reads_the_verification_state_with_the_internal_key(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    r = await client.get(f"{BASE}/caregivers/verification", params={"email": EMAIL})
    assert r.status_code == 401  # sin clave interna

    r = await client.get(f"{BASE}/caregivers/verification", params={"email": EMAIL}, headers=INTERNAL)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unpaid" and body["fee_clp"] == 9990 and body["reference"].startswith("AC-")

    await client.post(f"{BASE}/caregivers/{cid}/verification", headers=admin_headers, json={"action": "paid"})
    r = await client.get(f"{BASE}/caregivers/verification", params={"email": EMAIL}, headers=INTERNAL)
    assert r.json()["status"] == "paid" and r.json()["paid_at"] is not None


async def test_staff_can_confirm_waive_and_revert_the_fee(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    url = f"{BASE}/caregivers/{cid}/verification"

    d = (await client.post(url, headers=admin_headers, json={"action": "paid"})).json()
    assert d["verification_fee_status"] == "paid" and d["verification_paid_at"] and d["verification_marked_by"]

    d = (await client.post(url, headers=admin_headers, json={"action": "waived"})).json()
    assert d["verification_fee_status"] == "waived" and d["verification_paid_at"] is None

    d = (await client.post(url, headers=admin_headers, json={"action": "unpaid"})).json()
    assert d["verification_fee_status"] == "unpaid" and d["verification_marked_by"] is None

    r = await client.post(url, headers=admin_headers, json={"action": "regalo"})
    assert r.status_code == 422


async def test_waived_caregiver_can_be_approved_without_paying(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    for t in ("id_card", "background_check"):
        r = await client.post(f"{BASE}/documents/sync", headers=INTERNAL, json={
            "caregiver_email": EMAIL, "doc_type": t, "file_url": f"https://files/{t}.png",
            "original_filename": f"{t}.png", "is_change": False})
        assert r.status_code == 201
        r = await client.post(f"{BASE}/caregivers/{cid}/documents/{t}/review", headers=admin_headers,
                              json={"action": "approve"})
        assert r.status_code == 200
    await client.post(f"{BASE}/caregivers/{cid}/verification", headers=admin_headers, json={"action": "waived"})
    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 200


PRODUCT = {"name": "Silla de ducha plegable", "category": "home_safety", "vendor": "SaludHogar",
           "price_clp": 32990, "external_url": "https://saludhogar.cl/silla-ducha",
           "description": "Silla antideslizante con respaldo.", "is_sponsored": True,
           "conditions": ["Movilidad reducida"], "commission_pct": 7.5}


async def test_creating_a_product_sends_it_to_the_public_site(client, admin_headers, pushed):
    r = await client.post(f"{BASE}/products", headers=admin_headers, json=PRODUCT)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["is_sponsored"] is True and created["commission_pct"] == 7.5

    sent = pushed["products"][-1]
    assert sent["id"] == created["id"] and sent["is_active"] is True
    assert sent["category"] == "home_safety" and sent["conditions"] == ["Movilidad reducida"]
    assert sent["price_clp"] == 32990 and sent["is_sponsored"] is True


async def test_archiving_a_product_hides_it_on_the_site_and_sponsoring_can_be_toggled(client, admin_headers, pushed):
    pid = (await client.post(f"{BASE}/products", headers=admin_headers, json=PRODUCT)).json()["id"]

    r = await client.patch(f"{BASE}/products/{pid}", headers=admin_headers,
                           json={"status": "archived", "is_sponsored": False})
    assert r.status_code == 200
    assert pushed["products"][-1]["is_active"] is False and pushed["products"][-1]["is_sponsored"] is False


async def test_product_validation(client, admin_headers, pushed):
    bad_category = {**PRODUCT, "category": "Movilidad"}
    assert (await client.post(f"{BASE}/products", headers=admin_headers, json=bad_category)).status_code == 422
    insecure = {**PRODUCT, "external_url": "http://saludhogar.cl/silla"}
    assert (await client.post(f"{BASE}/products", headers=admin_headers, json=insecure)).status_code == 422
    assert (await client.post(f"{BASE}/products", headers=admin_headers,
                              json={**PRODUCT, "commission_pct": 140})).status_code == 422


async def test_product_list_includes_clicks_from_the_site(client, admin_headers, pushed):
    pid = (await client.post(f"{BASE}/products", headers=admin_headers, json=PRODUCT)).json()["id"]
    STATS.clear()
    STATS[pid] = {"product_id": pid, "clicks_total": 40, "clicks_30d": 12}

    items = (await client.get(f"{BASE}/products", headers=admin_headers, params={"page_size": 100})).json()["items"]
    mine = next(i for i in items if i["id"] == pid)
    assert mine["clicks_30d"] == 12 and mine["clicks_total"] == 40
    STATS.clear()


async def test_monetization_summary_counts_fees_and_estimates_commission(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    await client.post(f"{BASE}/caregivers/{cid}/verification", headers=admin_headers, json={"action": "paid"})
    pid = (await client.post(f"{BASE}/products", headers=admin_headers, json=PRODUCT)).json()["id"]
    STATS.clear()
    STATS[pid] = {"product_id": pid, "clicks_total": 200, "clicks_30d": 100}

    r = await client.get(f"{BASE}/monetization", headers=admin_headers)
    assert r.status_code == 200, r.text
    m = r.json()
    assert m["verification_paid_count"] >= 1
    assert m["verification_paid_total_clp"] == m["verification_paid_count"] * 9990
    assert m["products_sponsored"] >= 1 and m["clicks_30d"] >= 100
    # 100 clics x 3 % de conversión x $32.990 x 7,5 % de comisión (+ lo que aporten otros productos del seed)
    assert m["estimated_commission_30d_clp"] >= round(100 * 0.03 * 32990 * 0.075)
    assert m["assumed_conversion_pct"] == 3.0
    STATS.clear()


async def test_monetization_works_when_the_site_does_not_answer(client, admin_headers, monkeypatch):
    async def down():
        return None

    monkeypatch.setattr(general_client, "fetch_product_stats", down)
    m = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()
    assert m["clicks_30d"] is None and m["estimated_commission_30d_clp"] is None
