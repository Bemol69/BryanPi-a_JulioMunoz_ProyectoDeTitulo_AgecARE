"""Exenciones de la verificación: motivo obligatorio, vencimiento real, reglas de reversión y reportes."""
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import update

import app.database as database
from app import general_client, models
from app.security import now_utc

INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
BASE = "/api/v1/admin/marketplace"
EMAIL = "exencion.cuidadora@test.cl"
PROMO = {"action": "waived", "reason": "launch_promo", "days": 90}


@pytest.fixture
def pushed(monkeypatch):
    calls = {"qualified": [], "status": []}

    async def push_qualified(email, qualified, listing_until=None):
        calls["qualified"].append((email, qualified, listing_until))

    async def push_status(email, status):
        calls["status"].append((email, status))

    async def push_review(email, doc_type, action, note):
        return None

    monkeypatch.setattr(general_client, "push_qualified", push_qualified)
    monkeypatch.setattr(general_client, "push_status", push_status)
    monkeypatch.setattr(general_client, "push_document_review", push_review)
    return calls


async def new_caregiver(client, email=EMAIL):
    r = await client.post(f"{BASE}/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": "u-ex", "name": "Cuidadora Exencion", "email": email, "zone": "Ñuñoa",
        "specialties": [], "languages": [], "certifications_count": 0})
    assert r.status_code in (200, 201), r.text
    return r.json()["caregiver_id"]


async def fee(client, headers, cid, **body):
    return await client.post(f"{BASE}/caregivers/{cid}/verification", headers=headers, json=body)


async def detail(client, headers, cid):
    return (await client.get(f"{BASE}/caregivers/{cid}", headers=headers)).json()


async def expire_waiver(cid, days_ago=1):
    async with database.get_session_factory()() as db:
        await db.execute(update(models.CaregiverProfile).where(models.CaregiverProfile.id == UUID(cid))
                         .values(verification_waiver_until=now_utc() - timedelta(days=days_ago)))
        await db.commit()


async def approve_documents(client, headers, cid, email=EMAIL):
    for t in ("id_card", "background_check"):
        await client.post(f"{BASE}/documents/sync", headers=INTERNAL, json={
            "caregiver_email": email, "doc_type": t, "file_url": f"https://files/{t}.png",
            "original_filename": f"{t}.png", "is_change": False})
        r = await client.post(f"{BASE}/caregivers/{cid}/documents/{t}/review", headers=headers, json={"action": "approve"})
        assert r.status_code == 200


# ---------- Qué se exige al eximir ----------
async def test_a_waiver_needs_a_reason(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    assert (await fee(client, admin_headers, cid, action="waived")).status_code == 422


async def test_promo_and_scholarship_waivers_must_expire(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    for reason in ("launch_promo", "scholarship"):
        r = await fee(client, admin_headers, cid, action="waived", reason=reason)
        assert r.status_code == 422, reason
    # Un convenio con una institución sí puede no vencer.
    assert (await fee(client, admin_headers, cid, action="waived", reason="institution_agreement")).status_code == 200


async def test_a_special_case_needs_an_explanation(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    r = await fee(client, admin_headers, cid, action="waived", reason="special_case", note="corto")
    assert r.status_code == 422
    r = await fee(client, admin_headers, cid, action="waived", reason="special_case",
                  note="Cuidadora referida por el centro de salud municipal")
    assert r.status_code == 200 and r.json()["verification_waiver_note"].startswith("Cuidadora referida")


async def test_only_the_offered_durations_are_valid(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    assert (await fee(client, admin_headers, cid, action="waived", reason="launch_promo", days=45)).status_code == 422
    assert (await fee(client, admin_headers, cid, action="waived", reason="launch_promo", days=90)).status_code == 200


# ---------- Se guarda y se avisa al sitio ----------
async def test_a_waiver_with_expiry_is_stored_and_told_to_the_site(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    d = (await fee(client, admin_headers, cid, **PROMO)).json()
    assert d["verification_fee_status"] == "waived" and d["verification_waiver_reason"] == "launch_promo"
    assert d["verification_waiver_expired"] is False and d["verification_marked_by"]
    email, qualified, until = pushed["qualified"][-1]
    assert (email, qualified) == (EMAIL, False)  # eximida: sin insignia ni prioridad
    assert until is not None and timedelta(days=89) < until - now_utc() < timedelta(days=91)

    # Sin vencimiento: el sitio no recibe fecha.
    await fee(client, admin_headers, cid, action="waived", reason="institution_agreement")
    assert pushed["qualified"][-1][2] is None


async def test_paying_replaces_the_waiver_and_records_the_receipt(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    await fee(client, admin_headers, cid, **PROMO)
    d = (await fee(client, admin_headers, cid, action="paid", method="deposit", receipt="  DEP-5521 ")).json()
    assert d["verification_fee_status"] == "paid" and d["verification_payment_method"] == "deposit"
    assert d["verification_receipt"] == "DEP-5521"
    assert d["verification_waiver_reason"] is None and d["verification_waiver_until"] is None  # ya no rige
    assert pushed["qualified"][-1] == (EMAIL, True, None)


# ---------- Vencimiento ----------
async def test_an_expired_waiver_counts_as_pending_and_blocks_approval(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    await approve_documents(client, admin_headers, cid)
    await fee(client, admin_headers, cid, **PROMO)
    await expire_waiver(cid)

    d = await detail(client, admin_headers, cid)
    assert d["verification_waiver_expired"] is True
    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERIFICATION_FEE_PENDING"
    assert "venció" in r.json()["error"]["message"]

    # El sitio la ve como "por pagar" y se lo explica a la cuidadora.
    s = (await client.get(f"{BASE}/caregivers/verification", params={"email": EMAIL}, headers=INTERNAL)).json()
    assert s["status"] == "unpaid" and s["waiver_expired"] is True and s["waiver_reason"] == "launch_promo"

    # Renovar la exención o pagar la deja aprobar de nuevo.
    await fee(client, admin_headers, cid, **PROMO)
    r = await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})
    assert r.status_code == 200


async def test_statuses_tell_the_site_when_a_waiver_ends(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    await fee(client, admin_headers, cid, **PROMO)
    items = (await client.get(f"{BASE}/caregivers/statuses", headers=INTERNAL)).json()["items"]
    mine = next(i for i in items if i["email"] == EMAIL)
    assert mine["qualified"] is False and mine["listing_until"] is not None


# ---------- Reversión ----------
async def test_a_fee_cannot_be_reverted_while_the_profile_is_published(client, admin_headers, pushed):
    cid = await new_caregiver(client)
    await approve_documents(client, admin_headers, cid)
    await fee(client, admin_headers, cid, action="paid")
    await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers, json={"status": "approved"})

    r = await fee(client, admin_headers, cid, action="unpaid")
    assert r.status_code == 409 and r.json()["error"]["code"] == "FEE_REVERT_BLOCKED"

    # Suspendida sí se puede revertir, y queda sin datos de pago ni exención.
    await client.patch(f"{BASE}/caregivers/{cid}", headers=admin_headers,
                       json={"status": "suspended", "reason": "Revisión del cobro de verificación"})
    d = (await fee(client, admin_headers, cid, action="unpaid")).json()
    assert d["verification_fee_status"] == "unpaid" and d["verification_paid_at"] is None
    assert d["verification_payment_method"] is None and d["verification_marked_by"] is None


# ---------- Filtros y resumen ----------
async def test_caregivers_can_be_filtered_by_fee_state(client, admin_headers, pushed):
    unpaid = await new_caregiver(client, "ex.sinpago@test.cl")
    paid = await new_caregiver(client, "ex.pagada@test.cl")
    waived = await new_caregiver(client, "ex.eximida@test.cl")
    expired = await new_caregiver(client, "ex.vencida@test.cl")
    await fee(client, admin_headers, paid, action="paid")
    await fee(client, admin_headers, waived, **PROMO)
    await fee(client, admin_headers, expired, **PROMO)
    await expire_waiver(expired)

    async def ids(state):
        items = (await client.get(f"{BASE}/caregivers", headers=admin_headers, params={"fee": state})).json()["items"]
        return {i["caregiver_id"] for i in items}

    assert paid in await ids("paid") and unpaid not in await ids("paid")
    assert waived in await ids("waived") and expired not in await ids("waived")
    assert expired in await ids("expired") and waived not in await ids("expired")
    assert {unpaid, expired} <= await ids("unpaid") and paid not in await ids("unpaid")  # vencida cuenta como por pagar


async def test_the_summary_values_waivers_and_flags_the_expiring_ones(client, admin_headers, pushed):
    before = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()
    soon = await new_caregiver(client, "ex.pronto@test.cl")
    gone = await new_caregiver(client, "ex.gone@test.cl")
    await fee(client, admin_headers, soon, **PROMO)
    await fee(client, admin_headers, gone, **PROMO)
    async with database.get_session_factory()() as db:  # una vence en 5 días
        await db.execute(update(models.CaregiverProfile).where(models.CaregiverProfile.id == UUID(soon))
                         .values(verification_waiver_until=now_utc() + timedelta(days=5)))
        await db.commit()
    await expire_waiver(gone)

    m = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()
    assert m["verification_waived_count"] == before["verification_waived_count"] + 1
    assert m["verification_expired_count"] == before["verification_expired_count"] + 1
    assert m["verification_expiring_soon_count"] == before["verification_expiring_soon_count"] + 1
    assert m["verification_waived_value_clp"] == m["verification_waived_count"] * 9990
    assert m["verification_pending_count"] >= before["verification_pending_count"] + 1  # la vencida ya es por cobrar
    assert m["verification_waived_by_reason"]["launch_promo"] >= 1
