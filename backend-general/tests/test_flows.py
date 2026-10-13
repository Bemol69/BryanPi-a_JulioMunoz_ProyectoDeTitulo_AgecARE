"""Flujos del sitio público: visibilidad según el staff, documentos, reseñas, chat y ficha."""
from datetime import timedelta

from sqlalchemy import select, update

import app.database as database
from app import models
from app.security import now_utc
from tests.conftest import INTERNAL

API = "/api/v1"


async def names_in_search(client, headers):
    r = await client.get(f"{API}/marketplace/caregivers", headers=headers)
    assert r.status_code == 200, r.text
    return {c["full_name"]: c for c in r.json()["items"]}


async def profile_id_of(client, headers, name):
    return (await names_in_search(client, headers))[name]["profile_id"]


async def set_status(client, email, status):
    r = await client.post(f"{API}/internal/caregivers/status", json={"email": email, "status": status},
                          headers=INTERNAL)
    assert r.status_code == 204, r.text


# ---------- Visibilidad según la revisión del staff ----------
async def test_only_approved_caregivers_are_listed(client, family):
    assert len(await names_in_search(client, family)) == 4
    await set_status(client, "rocio@cuidado.cl", "suspended")
    await set_status(client, "fernanda@cuidado.cl", "pending")
    found = await names_in_search(client, family)
    assert "Rocío Álvarez" not in found and "Fernanda Ibáñez" not in found
    await set_status(client, "rocio@cuidado.cl", "approved")  # reactivar
    assert "Rocío Álvarez" in await names_in_search(client, family)


async def test_suspended_profile_detail_is_hidden(client, family):
    pid = await profile_id_of(client, family, "Javiera Soto")
    await set_status(client, "javiera@cuidado.cl", "suspended")
    r = await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)
    assert r.status_code == 404


async def test_internal_endpoints_require_the_shared_key(client):
    r = await client.post(f"{API}/internal/caregivers/status",
                          json={"email": "rocio@cuidado.cl", "status": "approved"})
    assert r.status_code == 401
    r = await client.post(f"{API}/internal/caregivers/status", headers={"X-Internal-Key": "otra"},
                          json={"email": "rocio@cuidado.cl", "status": "approved"})
    assert r.status_code == 401


async def test_working_caregivers_are_flagged_and_listed_last(client, family):
    r = await client.get(f"{API}/marketplace/caregivers", headers=family)
    items = r.json()["items"]
    maria = next(c for c in items if c["full_name"] == "María Torres")
    assert maria["is_engaged"] is True
    assert items[-1]["full_name"] == "María Torres"
    assert all(not c["is_engaged"] for c in items if c["full_name"] != "María Torres")


# ---------- Documentos con aprobación del staff ----------
async def upload(client, headers, doc_type="id_card", name="cedula.png"):
    return await client.post(f"{API}/caregiver/documents", headers=headers, data={"doc_type": doc_type},
                             files={"file": (name, b"\x89PNG-demo", "image/png")})


async def review(client, doc_type, action, note=None, email="maria@cuidado.cl"):
    r = await client.post(f"{API}/internal/documents/review", headers=INTERNAL,
                          json={"email": email, "doc_type": doc_type, "action": action, "note": note})
    assert r.status_code == 204, r.text


async def doc(client, headers, doc_type="id_card"):
    r = await client.get(f"{API}/caregiver/documents", headers=headers)
    return next(d for d in r.json() if d["doc_type"] == doc_type)


async def test_first_upload_is_pending_then_approved(client, maria):
    r = await upload(client, maria)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending" and r.json()["pending_file_url"] is None
    await review(client, "id_card", "approve")
    assert (await doc(client, maria))["status"] == "approved"


async def test_site_adopts_console_decision_when_the_notice_never_arrived(client, maria, monkeypatch):
    import app.routers.caregiver as caregiver_router
    r = await upload(client, maria)
    url = r.json()["file_url"]
    assert (await doc(client, maria))["status"] == "pending"

    async def console_says_approved(email):
        return [{"doc_type": "id_card", "file_url": url, "status": "approved",
                 "pending_file_url": None, "review_note": None}]
    monkeypatch.setattr(caregiver_router, "fetch_admin_documents", console_says_approved)
    assert (await doc(client, maria))["status"] == "approved"

    # una decisión sobre otro archivo (la cuidadora ya subió uno nuevo) no se adopta
    async def console_has_older_file(email):
        return [{"doc_type": "id_card", "file_url": "https://otro/archivo-viejo.png", "status": "approved",
                 "pending_file_url": None, "review_note": None}]
    monkeypatch.setattr(caregiver_router, "fetch_admin_documents", console_has_older_file)
    await upload(client, maria, name="otra.png")
    d = await doc(client, maria)
    assert d["status"] == "approved" and d["pending_file_url"] is not None


async def test_rejected_document_can_be_replaced(client, maria):
    await upload(client, maria)
    await review(client, "id_card", "reject", "Se ve borrosa")
    d = await doc(client, maria)
    assert d["status"] == "rejected" and d["review_note"] == "Se ve borrosa"
    await upload(client, maria, name="nueva.png")
    d = await doc(client, maria)
    assert d["status"] == "pending" and d["review_note"] is None and d["original_filename"] == "nueva.png"


async def test_changing_an_approved_document_needs_a_new_approval(client, maria):
    first = (await upload(client, maria)).json()
    await review(client, "id_card", "approve")
    await upload(client, maria, name="cambio.png")
    d = await doc(client, maria)
    # El aprobado sigue vigente mientras el cambio espera.
    assert d["status"] == "approved" and d["file_url"] == first["file_url"]
    assert d["pending_file_url"] and d["pending_filename"] == "cambio.png"

    await review(client, "id_card", "approve")
    d = await doc(client, maria)
    assert d["pending_file_url"] is None and d["original_filename"] == "cambio.png"

    await upload(client, maria, name="otro.png")
    await review(client, "id_card", "reject", "No corresponde")
    d = await doc(client, maria)
    assert d["status"] == "approved" and d["pending_file_url"] is None and d["original_filename"] == "cambio.png"


async def test_files_over_the_limit_are_rejected(client, maria):
    big = b"0" * (4 * 1024 * 1024 + 1)
    r = await client.post(f"{API}/caregiver/documents", headers=maria, data={"doc_type": "id_card"},
                          files={"file": ("grande.png", big, "image/png")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


# ---------- Reseñas solo al terminar el trabajo ----------
async def test_review_only_after_the_job_ended(client, family):
    pid = await profile_id_of(client, family, "María Torres")
    body = {"rating": 5, "comment": "Excelente"}

    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["can_review"] is False and detail["hired_by_me"] is True
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/reviews", json=body, headers=family)
    assert r.status_code == 409 and r.json()["error"]["code"] == "REVIEW_NOT_ALLOWED"

    r = await client.post(f"{API}/marketplace/engagements/{detail['my_engagement_id']}/end", headers=family)
    assert r.status_code == 204
    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["can_review"] is True and detail["hired_by_me"] is False

    r = await client.post(f"{API}/marketplace/caregivers/{pid}/reviews", json=body, headers=family)
    assert r.status_code == 201, r.text
    assert r.json()
    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["can_review"] is False
    assert detail["reviews"][0]["author_name"] == "Familia Muñoz"
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/reviews", json=body, headers=family)
    assert r.status_code == 409


async def test_never_hired_caregiver_cannot_be_reviewed(client, family):
    pid = await profile_id_of(client, family, "Javiera Soto")
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/reviews", json={"rating": 4}, headers=family)
    assert r.status_code == 409


# ---------- Chat con borrado a los 7 días ----------
async def test_contact_opens_a_chat_both_sides_can_use(client, family, javiera, maria):
    pid = await profile_id_of(client, family, "Javiera Soto")
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/contact", headers=family,
                          json={"message": "Hola, busco apoyo para mi mamá"})
    assert r.status_code == 201, r.text
    conv_id = r.json()["conversation_id"]

    chats = (await client.get(f"{API}/chats", headers=javiera)).json()["items"]
    assert [c["conversation_id"] for c in chats] == [conv_id]
    assert chats[0]["other_name"] == "Carolina Muñoz"
    assert chats[0]["last_message"]["body"] == "Hola, busco apoyo para mi mamá"

    r = await client.post(f"{API}/chats/{conv_id}/messages", headers=javiera, json={"body": "¡Hola! Cuéntame más"})
    assert r.status_code == 201 and r.json()["mine"] is True
    detail = (await client.get(f"{API}/chats/{conv_id}", headers=family)).json()
    assert [m["mine"] for m in detail["messages"]] == [True, False]
    assert detail["other_name"] == "Javiera Soto" and detail["retention_days"] == 7

    # Una tercera persona no participa.
    r = await client.get(f"{API}/chats/{conv_id}", headers=maria)
    assert r.status_code == 403

    # Contactar de nuevo retoma la misma conversación.
    r = await client.post(f"{API}/marketplace/caregivers/{pid}/contact", headers=family, json={"message": "Una duda más"})
    assert r.json()["conversation_id"] == conv_id
    assert len((await client.get(f"{API}/chats/{conv_id}", headers=family)).json()["messages"]) == 3


async def test_chat_messages_are_deleted_after_a_week(client, family, javiera):
    pid = await profile_id_of(client, family, "Javiera Soto")
    conv_id = (await client.post(f"{API}/marketplace/caregivers/{pid}/contact", headers=family,
                                 json={"message": "Mensaje viejo"})).json()["conversation_id"]
    await client.post(f"{API}/chats/{conv_id}/messages", headers=javiera, json={"body": "Mensaje reciente"})

    old = now_utc() - timedelta(days=8)
    async with database.get_session_factory()() as db:
        first = (await db.execute(select(models.ChatMessage)
                                  .order_by(models.ChatMessage.created_at.asc()))).scalars().first()
        await db.execute(update(models.ChatMessage).where(models.ChatMessage.id == first.id)
                         .values(created_at=old))
        await db.commit()

    detail = (await client.get(f"{API}/chats/{conv_id}", headers=family)).json()
    assert [m["body"] for m in detail["messages"]] == ["Mensaje reciente"]

    async with database.get_session_factory()() as db:
        await db.execute(update(models.ChatMessage).values(created_at=old))
        await db.execute(update(models.ChatConversation).values(last_message_at=old))
        await db.commit()
    assert (await client.get(f"{API}/chats", headers=family)).json()["items"] == []
    assert (await client.get(f"{API}/chats/{conv_id}", headers=family)).status_code == 404


async def test_only_families_start_chats_and_only_with_listed_caregivers(client, family, maria):
    pid = await profile_id_of(client, family, "Rocío Álvarez")
    r = await client.post(f"{API}/chats/start", headers=maria, json={"profile_id": pid, "message": "Hola"})
    assert r.status_code == 403
    await set_status(client, "rocio@cuidado.cl", "suspended")
    r = await client.post(f"{API}/chats/start", headers=family, json={"profile_id": pid, "message": "Hola"})
    assert r.status_code == 404


# ---------- Ficha del adulto mayor ----------
async def test_patient_detail_shows_profile_and_care_status(client, family):
    patients = (await client.get(f"{API}/patients", headers=family)).json()["items"]
    elena = next(p for p in patients if p["full_name"] == "Elena Muñoz")
    r = await client.get(f"{API}/patients/{elena['patient_id']}", headers=family)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["age"] >= 70 and d["medication_allergies"] == ["Penicilina"]
    assert d["caregiver"]["full_name"] == "María Torres"

    # Sin trabajo activo queda "sin cuidadora".
    pid = await profile_id_of(client, family, "María Torres")
    eid = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()["my_engagement_id"]
    await client.post(f"{API}/marketplace/engagements/{eid}/end", headers=family)
    d = (await client.get(f"{API}/patients/{elena['patient_id']}", headers=family)).json()
    assert d["caregiver"] is None


# ---------- Una cuidadora, un trabajo a la vez ----------
async def register_family(client, email):
    r = await client.post(f"{API}/auth/register", json={
        "full_name": "Otra Familia", "email": email, "password": "Familia123!", "account_type": "family"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def ask(client, headers, pid, **body):
    return await client.post(f"{API}/marketplace/caregivers/{pid}/hire-requests", json=body, headers=headers)


async def test_a_working_caregiver_cannot_be_requested_by_another_family(client, family):
    other = await register_family(client, "otra@familia.cl")
    maria_id = await profile_id_of(client, other, "María Torres")  # ya trabaja con la familia demo
    r = await ask(client, other, maria_id)
    assert r.status_code == 409 and r.json()["error"]["code"] == "CAREGIVER_BUSY"
    # Ya no existe la contratación directa: solo solicitudes que la cuidadora acepta.
    r = await client.post(f"{API}/marketplace/caregivers/{maria_id}/hire", json={}, headers=other)
    assert r.status_code in (404, 405)


async def test_hire_request_is_accepted_by_the_caregiver(client, family, javiera):
    pid = await profile_id_of(client, family, "Javiera Soto")
    r = await ask(client, family, pid, message="Necesito apoyo de lunes a viernes")
    assert r.status_code == 201 and r.json()["status"] == "pending", r.text
    conv_id = r.json()["conversation_id"]
    assert conv_id, "la solicitud abre el chat"

    # La familia ve la solicitud pendiente y no puede enviar otra.
    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["my_request"]["status"] == "pending" and detail["hired_by_me"] is False
    assert (await ask(client, family, pid)).json()["error"]["code"] == "REQUEST_PENDING"
    # Todavía no está en servicio: la solicitud no inicia el trabajo.
    assert (await names_in_search(client, family))["Javiera Soto"]["is_engaged"] is False

    # La cuidadora la ve con los datos de a quién cuidaría.
    inbox = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"]
    assert len(inbox) == 1 and inbox[0]["status"] == "pending"
    assert inbox[0]["family_name"] == "Familia Muñoz" and inbox[0]["message"] == "Necesito apoyo de lunes a viernes"
    assert inbox[0]["conversation_id"] == conv_id
    msgs = (await client.get(f"{API}/chats/{conv_id}", headers=javiera)).json()["messages"]
    assert msgs[0]["body"] == "Te envié una solicitud de contratación. Necesito apoyo de lunes a viernes"

    # Al aceptar empieza el trabajo y se abre el chat.
    r = await client.post(f"{API}/caregiver/hire-requests/{inbox[0]['request_id']}/accept", headers=javiera)
    assert r.status_code == 200, r.text
    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["hired_by_me"] is True and detail["is_engaged"] is True and detail["my_request"] is None
    assert detail["conversation_id"]
    msgs = (await client.get(f"{API}/chats/{conv_id}", headers=family)).json()["messages"]
    assert msgs[-1]["mine"] is False and "Acepté tu solicitud" in msgs[-1]["body"]
    assert (await names_in_search(client, family))["Javiera Soto"]["is_engaged"] is True
    again = await client.post(f"{API}/caregiver/hire-requests/{inbox[0]['request_id']}/accept", headers=javiera)
    assert again.status_code == 409 and again.json()["error"]["code"] == "REQUEST_NOT_PENDING"

    # Mientras trabaja no se le puede solicitar; al terminar vuelve a estar disponible.
    other = await register_family(client, "otra@familia.cl")
    assert (await ask(client, other, pid)).json()["error"]["code"] == "CAREGIVER_BUSY"
    eid = detail["my_engagement_id"]
    assert (await client.post(f"{API}/marketplace/engagements/{eid}/end", headers=family)).status_code == 204
    assert (await ask(client, other, pid)).status_code == 201


async def test_caregiver_can_decline_and_family_can_cancel(client, family, javiera, maria):
    pid = await profile_id_of(client, family, "Javiera Soto")
    await ask(client, family, pid)
    rid = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]["request_id"]
    assert (await client.post(f"{API}/caregiver/hire-requests/{rid}/decline", headers=javiera)).status_code == 204
    detail = (await client.get(f"{API}/marketplace/caregivers/{pid}", headers=family)).json()
    assert detail["my_request"]["status"] == "declined"
    # Otra cuidadora no puede responder una solicitud ajena.
    assert (await client.post(f"{API}/caregiver/hire-requests/{rid}/accept", headers=maria)).status_code == 404

    # Se puede volver a solicitar, y la familia puede cancelarla mientras esté pendiente.
    r = await ask(client, family, pid)
    assert r.status_code == 201
    new_id = r.json()["request_id"]
    assert (await client.post(f"{API}/marketplace/hire-requests/{new_id}/cancel", headers=family)).status_code == 204
    assert (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]["status"] == "declined"
    assert (await client.post(f"{API}/marketplace/hire-requests/{new_id}/cancel", headers=family)).status_code == 409


async def test_accepting_one_request_leaves_the_others_unavailable(client, family, javiera):
    pid = await profile_id_of(client, family, "Javiera Soto")
    other = await register_family(client, "otra@familia.cl")
    await ask(client, family, pid)
    await ask(client, other, pid)
    inbox = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"]
    assert len(inbox) == 2
    await client.post(f"{API}/caregiver/hire-requests/{inbox[0]['request_id']}/accept", headers=javiera)
    after = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"]
    assert sorted(r["status"] for r in after) == ["accepted", "unavailable"]
    # La segunda ya no se puede aceptar.
    other_req = next(r for r in after if r["status"] == "unavailable")
    r = await client.post(f"{API}/caregiver/hire-requests/{other_req['request_id']}/accept", headers=javiera)
    assert r.status_code == 409
