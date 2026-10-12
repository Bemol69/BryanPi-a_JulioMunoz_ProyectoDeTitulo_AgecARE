"""Revisión de cuidadoras en la Consola: documentos, aprobar / suspender / reactivar y aviso al sitio."""
import pytest

from app import general_client

INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
BASE = "/api/v1/admin/marketplace"
EMAIL = "nueva.cuidadora@test.cl"


@pytest.fixture
def pushed(monkeypatch):
    """Registra los avisos al sitio público en vez de hacer llamadas de red."""
    calls = {"status": [], "review": []}

    async def push_status(email, status):
        calls["status"].append((email, status))

    async def push_review(email, doc_type, action, note):
        calls["review"].append((email, doc_type, action, note))

    monkeypatch.setattr(general_client, "push_status", push_status)
    monkeypatch.setattr(general_client, "push_document_review", push_review)
    return calls


async def sync_profile(client):
    r = await client.post(f"{BASE}/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": "u-1", "name": "Nueva Cuidadora", "email": EMAIL, "zone": "Providencia",
        "specialties": ["Alzheimer"], "languages": ["Español"], "certifications_count": 0})
    assert r.status_code in (200, 201), r.text
    return r.json()["caregiver_id"]


async def sync_doc(client, doc_type, name="doc.png", is_change=False):
    r = await client.post(f"{BASE}/documents/sync", headers=INTERNAL, json={
        "caregiver_email": EMAIL, "doc_type": doc_type, "file_url": f"https://files/{name}",
        "original_filename": name, "is_change": is_change})
    assert r.status_code == 201, r.text
    return r.json()


async def review(client, headers, cid, doc_type, action, note=None):
    return await client.post(f"{BASE}/caregivers/{cid}/documents/{doc_type}/review", headers=headers,
                             json={"action": action, "note": note})


async def detail(client, headers, cid):
    r = await client.get(f"{BASE}/caregivers/{cid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_profile_cannot_be_approved_until_the_required_documents_are_approved(client, admin_headers, pushed):
    cid = await sync_profile(client)
    await sync_doc(client, "id_card")
    await sync_doc(client, "background_check")

    d = await detail(client, admin_headers, cid)
    assert d["certifications_verified"] is False and d["pending_documents"] == 2
    assert {x["doc_type"]: x["status"] for x in d["documents"]} == {"id_card": "pending", "background_check": "pending"}

    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CERTIFICATION_REQUIRED"

    assert (await review(client, admin_headers, cid, "id_card", "approve")).status_code == 200
    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 409  # falta el certificado de antecedentes

    assert (await review(client, admin_headers, cid, "background_check", "approve")).status_code == 200
    d = await detail(client, admin_headers, cid)
    assert d["certifications_verified"] is True and d["pending_documents"] == 0

    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert pushed["status"][-1] == (EMAIL, "approved")
    assert [c[2] for c in pushed["review"]] == ["approve", "approve"]


async def test_suspend_and_reactivate_notify_the_public_site(client, admin_headers, pushed):
    cid = await sync_profile(client)
    for t in ("id_card", "background_check"):
        await sync_doc(client, t)
        await review(client, admin_headers, cid, t, "approve")
    await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})

    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers,
                           json={"status": "suspended", "reason": "Reiteradas ausencias reportadas"})
    assert r.status_code == 200 and r.json()["status"] == "suspended"
    assert pushed["status"][-1] == (EMAIL, "suspended")

    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 200 and r.json()["status"] == "approved"  # reactivar
    assert pushed["status"][-1] == (EMAIL, "approved")


async def test_rejecting_a_document_requires_a_reason(client, admin_headers, pushed):
    cid = await sync_profile(client)
    await sync_doc(client, "id_card")
    r = await review(client, admin_headers, cid, "id_card", "reject")
    assert r.status_code == 422 and r.json()["error"]["code"] == "REASON_REQUIRED"
    r = await review(client, admin_headers, cid, "id_card", "reject", "La imagen no es legible")
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert r.json()["review_note"] == "La imagen no es legible"
    # Ya revisado y sin cambios: no hay nada más que decidir.
    r = await review(client, admin_headers, cid, "id_card", "approve")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOTHING_TO_REVIEW"


async def test_replacing_an_approved_document_creates_a_pending_change(client, admin_headers, pushed):
    cid = await sync_profile(client)
    await sync_doc(client, "id_card", "original.png")
    await review(client, admin_headers, cid, "id_card", "approve")

    await sync_doc(client, "id_card", "cambio.png", is_change=True)
    d = (await detail(client, admin_headers, cid))["documents"][0]
    assert d["status"] == "approved" and d["file_url"].endswith("original.png")
    assert d["pending_file_url"].endswith("cambio.png")

    r = await review(client, admin_headers, cid, "id_card", "approve")
    assert r.json()["file_url"].endswith("cambio.png") and r.json()["pending_file_url"] is None

    await sync_doc(client, "id_card", "otro.png", is_change=True)
    r = await review(client, admin_headers, cid, "id_card", "reject", "No corresponde al titular")
    assert r.json()["status"] == "approved" and r.json()["file_url"].endswith("cambio.png")
    assert r.json()["pending_file_url"] is None


async def test_list_shows_how_many_documents_need_review(client, admin_headers, pushed):
    cid = await sync_profile(client)
    await sync_doc(client, "id_card")
    r = await client.get(f"{BASE}/caregivers", headers=admin_headers, params={"q": EMAIL})
    item = next(i for i in r.json()["items"] if i["caregiver_id"] == cid)
    assert item["pending_documents"] == 1


async def test_statuses_endpoint_is_internal_only(client, admin_headers):
    await sync_profile(client)
    assert (await client.get(f"{BASE}/caregivers/statuses")).status_code == 401
    r = await client.get(f"{BASE}/caregivers/statuses", headers=INTERNAL)
    assert r.status_code == 200
    assert EMAIL in {i["email"] for i in r.json()["items"]}  # (el estado depende de las pruebas previas)
    assert all(set(i) == {"email", "status"} for i in r.json()["items"])
