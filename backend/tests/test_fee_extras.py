"""Cupos de exención, historial, exportación CSV y permisos por rol del cobro de verificación."""
import csv
import io

import pytest

from app import general_client
from app.config import get_settings

INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
BASE = "/api/v1/admin/marketplace"
PROMO = {"action": "waived", "reason": "launch_promo", "days": 90}


@pytest.fixture
def pushed(monkeypatch):
    async def push_qualified(email, qualified, listing_until=None):
        return None

    async def push_status(email, status):
        return None

    monkeypatch.setattr(general_client, "push_qualified", push_qualified)
    monkeypatch.setattr(general_client, "push_status", push_status)


@pytest.fixture
async def editor_headers(client):
    r = await client.post("/api/v1/admin/auth/login", json={"email": "editora@wellq.co.uk", "password": "Editora123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def new_caregiver(client, email, name="Cuidadora Extra"):
    r = await client.post(f"{BASE}/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": email, "name": name, "email": email, "zone": "Ñuñoa",
        "specialties": [], "languages": [], "certifications_count": 0})
    assert r.status_code in (200, 201), r.text
    return r.json()["caregiver_id"]


async def fee(client, headers, cid, **body):
    return await client.post(f"{BASE}/caregivers/{cid}/verification", headers=headers, json=body)


# ---------- Permisos por rol ----------
async def test_an_editor_can_confirm_payments_but_not_waive_or_revert(client, editor_headers, pushed):
    cid = await new_caregiver(client, "rol.editor@test.cl")
    r = await fee(client, editor_headers, cid, **PROMO)
    assert r.status_code == 403
    assert (await fee(client, editor_headers, cid, action="paid", method="transfer", receipt="TR-1")).status_code == 200
    assert (await fee(client, editor_headers, cid, action="unpaid")).status_code == 403


async def test_an_administrator_can_do_all_three(client, admin_headers, pushed):
    cid = await new_caregiver(client, "rol.admin@test.cl")
    assert (await fee(client, admin_headers, cid, **PROMO)).status_code == 200
    assert (await fee(client, admin_headers, cid, action="paid")).status_code == 200
    assert (await fee(client, admin_headers, cid, action="unpaid")).status_code == 200


# ---------- Cupos ----------
async def test_waivers_stop_when_the_quota_of_a_reason_is_full(client, admin_headers, pushed, monkeypatch):
    summary = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()
    used = summary["verification_waiver_quotas"]["launch_promo"]["used"]
    monkeypatch.setattr(get_settings(), "waiver_quota_launch_promo", used + 1)  # queda un solo cupo

    first = await new_caregiver(client, "cupo.uno@test.cl")
    second = await new_caregiver(client, "cupo.dos@test.cl")
    assert (await fee(client, admin_headers, first, **PROMO)).status_code == 200
    r = await fee(client, admin_headers, second, **PROMO)
    assert r.status_code == 409 and r.json()["error"]["code"] == "WAIVER_QUOTA_REACHED"

    # Renovar la propia exención no consume otro cupo, y otro motivo con cupo libre sigue disponible.
    assert (await fee(client, admin_headers, first, **PROMO)).status_code == 200
    assert (await fee(client, admin_headers, second, action="waived", reason="institution_agreement")).status_code == 200

    q = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()["verification_waiver_quotas"]
    assert q["launch_promo"] == {"used": used + 1, "limit": used + 1}


async def test_a_reason_with_no_limit_has_no_quota_in_the_summary(client, admin_headers, pushed):
    quotas = (await client.get(f"{BASE}/monetization", headers=admin_headers)).json()["verification_waiver_quotas"]
    assert set(quotas) == {"launch_promo", "scholarship"}  # convenio y caso especial no tienen tope


# ---------- Historial ----------
async def test_the_history_lists_every_movement(client, admin_headers, pushed):
    cid = await new_caregiver(client, "historial@test.cl")
    await fee(client, admin_headers, cid, **PROMO)
    await fee(client, admin_headers, cid, action="paid", method="deposit", receipt="DEP-77")
    await fee(client, admin_headers, cid, action="unpaid")

    r = await client.get(f"{BASE}/caregivers/{cid}/verification-history", headers=admin_headers)
    assert r.status_code == 200
    by_status = {e["status"]: e for e in r.json()}  # (el orden por fecha lo da el registro; aquí solo importa el contenido)
    assert set(by_status) == {"waived", "paid", "unpaid"} and len(r.json()) == 3
    assert by_status["unpaid"]["previous_status"] == "paid" and by_status["unpaid"]["actor_name"] == "Max K."
    assert by_status["paid"]["method"] == "deposit" and by_status["paid"]["receipt"] == "DEP-77"
    assert by_status["waived"]["reason"] == "launch_promo" and by_status["waived"]["until"] is not None


async def test_the_history_needs_a_session(client):
    r = await client.get(f"{BASE}/caregivers/00000000-0000-0000-0000-000000000001/verification-history")
    assert r.status_code in (401, 403)


# ---------- Exportación CSV ----------
async def test_the_export_is_an_excel_friendly_csv_with_every_caregiver(client, admin_headers, pushed):
    cid = await new_caregiver(client, "csv.pago@test.cl", name="Cuidadora CSV")
    await fee(client, admin_headers, cid, action="paid", method="transfer", receipt="TR-9001")

    r = await client.get(f"{BASE}/verification/export", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and ".csv" in r.headers["content-disposition"]
    assert r.text.startswith("\ufeff")  # BOM: Excel respeta las tildes

    rows = list(csv.reader(io.StringIO(r.text.lstrip("\ufeff")), delimiter=";"))
    assert rows[0][:3] == ["Cuidadora", "Correo", "Estado del cobro"]
    mine = next(row for row in rows if row[1] == "csv.pago@test.cl")
    assert mine[2] == "Pagada" and mine[3] == "9990" and mine[5] == "Transferencia" and mine[6] == "TR-9001"


async def test_the_export_neutralises_spreadsheet_formulas(client, admin_headers, pushed):
    await new_caregiver(client, "csv.formula@test.cl", name="=HYPERLINK(\"http://x\")")
    text = (await client.get(f"{BASE}/verification/export", headers=admin_headers)).text
    assert "\n'=HYPERLINK" in text or ";'=HYPERLINK" in text or "'=HYPERLINK" in text
    assert "\n=HYPERLINK" not in text


async def test_the_export_is_only_for_staff(client):
    assert (await client.get(f"{BASE}/verification/export")).status_code in (401, 403)
