"""Una familia contrata a una sola cuidadora a la vez."""
from uuid import UUID

from sqlalchemy import select, update

import app.database as database
from app import models
from tests.conftest import login
from tests.test_flows import API, ask, end_demo_job, names_in_search, profile_id_of, register_family


async def detail(client, headers, pid):
    r = await client.get(f"{API}/marketplace/caregivers/{pid}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_a_family_that_already_has_a_caregiver_cannot_request_another(client, family):
    # La familia demo ya tiene contratada a María.
    javiera_id = await profile_id_of(client, family, "Javiera Soto")
    r = await ask(client, family, javiera_id)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PATIENT_ALREADY_HAS_CAREGIVER"
    assert "María Torres" in r.json()["error"]["message"]

    # La ficha lo anticipa: en la de otra cuidadora dice quién la tiene; en la de María, que es la suya.
    assert (await detail(client, family, javiera_id))["family_caregiver_name"] == "María Torres"
    maria = await detail(client, family, await profile_id_of(client, family, "María Torres"))
    assert maria["hired_by_me"] is True and maria["family_caregiver_name"] is None


async def test_finishing_the_job_frees_the_family_to_hire_again(client, family):
    javiera_id = await profile_id_of(client, family, "Javiera Soto")
    await end_demo_job(client, family)
    assert (await detail(client, family, javiera_id))["family_caregiver_name"] is None
    assert (await ask(client, family, javiera_id)).status_code == 201


async def test_a_family_without_a_caregiver_is_not_blocked(client):
    other = await register_family(client, "nueva@familia.cl")
    javiera_id = await profile_id_of(client, other, "Javiera Soto")
    assert (await detail(client, other, javiera_id))["family_caregiver_name"] is None
    assert (await ask(client, other, javiera_id)).status_code == 201


async def test_when_one_caregiver_accepts_the_familys_other_requests_are_cancelled(client, family):
    await end_demo_job(client, family)
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    rocio = await login(client, "rocio@cuidado.cl", "Cuidado123!")
    javiera_id = await profile_id_of(client, family, "Javiera Soto")
    rocio_id = await profile_id_of(client, family, "Rocío Álvarez")
    # Pedir a varias a la vez sigue permitido: la familia compara opciones.
    assert (await ask(client, family, javiera_id)).status_code == 201
    assert (await ask(client, family, rocio_id)).status_code == 201

    req = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]
    rocio_req = (await client.get(f"{API}/caregiver/hire-requests", headers=rocio)).json()["items"][0]
    assert (await client.post(f"{API}/caregiver/hire-requests/{req['request_id']}/accept", headers=javiera)).status_code == 200

    # La solicitud de Rocío se cancela sola: desaparece de su bandeja y ya no se puede aceptar.
    assert (await client.get(f"{API}/caregiver/hire-requests", headers=rocio)).json()["items"] == []
    r = await client.post(f"{API}/caregiver/hire-requests/{rocio_req['request_id']}/accept", headers=rocio)
    assert r.status_code == 409 and r.json()["error"]["code"] == "REQUEST_NOT_PENDING"
    assert (await names_in_search(client, family))["Rocío Álvarez"]["is_engaged"] is False


async def test_a_caregiver_cannot_accept_when_the_family_already_hired_someone_else(client, family):
    await end_demo_job(client, family)
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    rocio = await login(client, "rocio@cuidado.cl", "Cuidado123!")
    await ask(client, family, await profile_id_of(client, family, "Javiera Soto"))
    await ask(client, family, await profile_id_of(client, family, "Rocío Álvarez"))
    first = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]
    rocio_req = (await client.get(f"{API}/caregiver/hire-requests", headers=rocio)).json()["items"][0]

    # Caso límite: la solicitud de Rocío sigue "pendiente" cuando Javiera ya fue aceptada.
    await client.post(f"{API}/caregiver/hire-requests/{first['request_id']}/accept", headers=javiera)
    async with database.get_session_factory()() as db:
        await db.execute(update(models.HireRequest).where(models.HireRequest.id == UUID(rocio_req["request_id"]))
                         .values(status="pending", responded_at=None))
        await db.commit()

    r = await client.post(f"{API}/caregiver/hire-requests/{rocio_req['request_id']}/accept", headers=rocio)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PATIENT_ALREADY_HAS_CAREGIVER"
    # Queda cancelada aunque se respondió con error: ya no aparece en su bandeja.
    assert (await client.get(f"{API}/caregiver/hire-requests", headers=rocio)).json()["items"] == []
    assert (await names_in_search(client, family))["Rocío Álvarez"]["is_engaged"] is False


async def test_a_second_account_sharing_the_relative_cannot_hire_another_caregiver(client, family):
    other = await register_family(client, "hermana@familia.cl")
    async with database.get_session_factory()() as db:
        elena = (await db.execute(select(models.Patient).where(models.Patient.full_name == "Elena Muñoz"))).scalar_one()
        user = (await db.execute(select(models.User).where(models.User.email == "hermana@familia.cl"))).scalar_one()
        db.add(models.PatientMember(patient_id=elena.id, user_id=user.id, role="family", is_owner=False))
        await db.commit()

    javiera_id = await profile_id_of(client, other, "Javiera Soto")
    r = await ask(client, other, javiera_id)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PATIENT_ALREADY_HAS_CAREGIVER"


# ---------- Cada adulto mayor tiene su cuidadora: con dos abuelos, dos cuidadoras ----------
async def patient_ids(client, family):
    items = (await client.get(f"{API}/patients", headers=family)).json()["items"]
    return {p["full_name"]: p["patient_id"] for p in items}


async def add_grandparent(client, family, name="Abuelo Segundo"):
    r = await client.post(f"{API}/patients", headers=family, json={"full_name": name, "birth_date": "1945-05-05"})
    assert r.status_code == 201, r.text
    return r.json()["patient_id"]


async def test_a_family_with_two_grandparents_can_hire_one_caregiver_for_each(client, family):
    # Elena ya tiene a María. El segundo abuelo está libre: la familia sí puede contratar para él.
    second = await add_grandparent(client, family)
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    javiera_id = await profile_id_of(client, family, "Javiera Soto")
    assert (await detail(client, family, javiera_id))["family_caregiver_name"] is None  # hay un abuelo libre

    # Sin elegir, la solicitud va al abuelo que aún no tiene cuidadora (no al que ya tiene a María).
    assert (await ask(client, family, javiera_id)).status_code == 201
    req = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]
    assert req["patient_name"] == "Abuelo Segundo"
    assert (await client.post(f"{API}/caregiver/hire-requests/{req['request_id']}/accept", headers=javiera)).status_code == 200

    # Ahora los dos abuelos tienen cuidadora: una tercera no se puede contratar para ninguno.
    rocio_id = await profile_id_of(client, family, "Rocío Álvarez")
    elena = (await patient_ids(client, family))["Elena Muñoz"]
    for body in ({}, {"patient_id": elena}, {"patient_id": second}):
        r = await ask(client, family, rocio_id, **body)
        assert r.status_code == 409 and r.json()["error"]["code"] == "PATIENT_ALREADY_HAS_CAREGIVER", body
    assert (await detail(client, family, rocio_id))["family_caregiver_name"] is not None


async def test_requests_for_different_grandparents_do_not_cancel_each_other(client, family):
    second = await add_grandparent(client, family)
    elena = (await patient_ids(client, family))["Elena Muñoz"]
    await end_demo_job(client, family)  # Elena queda libre
    javiera = await login(client, "javiera@cuidado.cl", "Cuidado123!")
    rocio = await login(client, "rocio@cuidado.cl", "Cuidado123!")
    assert (await ask(client, family, await profile_id_of(client, family, "Javiera Soto"), patient_id=second)).status_code == 201
    assert (await ask(client, family, await profile_id_of(client, family, "Rocío Álvarez"), patient_id=elena)).status_code == 201

    req = (await client.get(f"{API}/caregiver/hire-requests", headers=javiera)).json()["items"][0]
    assert (await client.post(f"{API}/caregiver/hire-requests/{req['request_id']}/accept", headers=javiera)).status_code == 200
    # La de Rocío es para otro abuelo: sigue pendiente.
    assert [r["status"] for r in (await client.get(f"{API}/caregiver/hire-requests", headers=rocio)).json()["items"]] == ["pending"]


async def test_the_hiring_history_does_not_block(client, family):
    javiera_id = await profile_id_of(client, family, "Javiera Soto")
    await end_demo_job(client, family)  # el trabajo con María pasa al historial
    assert (await ask(client, family, javiera_id)).status_code == 201


async def test_a_request_cannot_target_a_relative_of_another_family(client, family):
    other = await register_family(client, "ajena@familia.cl")
    elena = (await patient_ids(client, family))["Elena Muñoz"]
    r = await ask(client, other, await profile_id_of(client, other, "Javiera Soto"), patient_id=elena)
    assert r.status_code == 403
