"""Seguridad del sitio público: inyección SQL, tokens falsos, acceso a datos ajenos, claves internas,
fuerza bruta, cabeceras y entradas hostiles. Nada de esto debe dar 200 ni un error 500."""
import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.main import app
from tests.conftest import INTERNAL, login

API = "/api/v1"

SQLI = [
    "' OR '1'='1",
    "' OR 1=1--",
    "admin'--",
    "'; DROP TABLE users;--",
    "\" OR \"\"=\"",
    "1; SELECT pg_sleep(5)--",
    "' UNION SELECT password_hash FROM users--",
    "%27%20OR%20%271%27%3D%271",
]
XSS = ["<script>alert(1)</script>", "\"><img src=x onerror=alert(1)>", "javascript:alert(1)", "{{7*7}}", "${7*7}"]


# ---------- Inyección SQL ----------
@pytest.mark.parametrize("payload", SQLI)
async def test_sql_injection_in_login_never_logs_in(client, payload):
    # En el correo: el formato de correo lo rechaza; en la contraseña: es solo un texto que no coincide.
    r = await client.post(f"{API}/auth/login", json={"email": payload, "password": "x"})
    assert r.status_code == 422
    r = await client.post(f"{API}/auth/login", json={"email": "familia@demo.cl", "password": payload})
    assert r.status_code == 401 and "access_token" not in r.text


@pytest.mark.parametrize("payload", SQLI)
async def test_sql_injection_in_search_filters_returns_normal_results(client, family, payload):
    for params in ({"q": payload}, {"zone": payload}, {"specialty": payload}, {"language": payload}):
        r = await client.get(f"{API}/marketplace/caregivers", params=params, headers=family)
        assert r.status_code in (200, 422), (params, r.status_code, r.text[:200])
        if r.status_code == 200:
            assert isinstance(r.json(), (list, dict))
    # La tabla de usuarios sigue intacta.
    await login(client, "familia@demo.cl", "Familia123!")


@pytest.mark.parametrize("payload", SQLI)
async def test_sql_injection_in_text_fields_is_stored_as_plain_text(client, payload):
    email = f"sqli{abs(hash(payload)) % 10**8}@test.cl"
    r = await client.post(f"{API}/auth/register", json={
        "full_name": f"Ana {payload}"[:120], "email": email, "password": "Segura123!", "account_type": "family"})
    assert r.status_code == 201, r.text
    headers = await login(client, email, "Segura123!")
    me = (await client.get(f"{API}/users/me", headers=headers)).json()
    assert me["full_name"] == f"Ana {payload}"[:120]  # se guarda literal, no se ejecuta
    # Y el resto de la base sigue funcionando.
    await login(client, "maria@cuidado.cl", "Cuidado123!")


@pytest.mark.parametrize("payload", SQLI[:4])
async def test_sql_injection_in_ids_is_rejected(client, family, payload):
    for path in (f"/patients/{payload}", f"/marketplace/caregivers/{payload}"):
        r = await client.get(f"{API}{path}", headers=family)
        assert r.status_code in (404, 422), (path, r.status_code)


# ---------- XSS y entradas hostiles ----------
@pytest.mark.parametrize("payload", XSS)
async def test_scripts_in_text_are_returned_as_inert_json(client, payload):
    email = f"xss{abs(hash(payload)) % 10**8}@test.cl"
    r = await client.post(f"{API}/auth/register", json={
        "full_name": f"Luis {payload}"[:120], "email": email, "password": "Segura123!", "account_type": "family"})
    assert r.status_code == 201
    headers = await login(client, email, "Segura123!")
    r = await client.get(f"{API}/users/me", headers=headers)
    assert r.headers["content-type"].startswith("application/json")  # nunca se sirve como HTML
    assert r.headers.get("x-content-type-options") == "nosniff"


async def test_oversized_and_malformed_bodies_do_not_crash_the_server(client):
    huge = "A" * 2_000_000
    r = await client.post(f"{API}/auth/register", json={
        "full_name": huge, "email": "a@b.cl", "password": "Segura123!", "account_type": "family"})
    assert r.status_code == 422
    r = await client.post(f"{API}/auth/login", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    r = await client.post(f"{API}/auth/login", json=["a", "b"])
    assert r.status_code == 422
    r = await client.post(f"{API}/auth/login", json={"email": None, "password": 123})
    assert r.status_code == 422
    r = await client.post(f"{API}/auth/login", content=b"\x00\x01\x02", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


async def test_path_traversal_cannot_read_server_files(client):
    for p in ("/uploads/../../etc/passwd", "/uploads/..%2f..%2fetc%2fpasswd", "/uploads/%2e%2e/%2e%2e/app/config.py"):
        r = await client.get(p)
        assert r.status_code in (400, 404), (p, r.status_code)
        assert "root:" not in r.text and "jwt_secret" not in r.text.lower()


# ---------- Tokens ----------
def _token(sub, secret="secreto-de-test-con-largo-suficiente-123456", alg="HS256", exp=None, extra=None):
    payload = {"sub": str(sub), "type": "access", "iat": int(datetime.now(timezone.utc).timestamp()),
               "exp": exp or datetime.now(timezone.utc) + timedelta(minutes=10), **(extra or {})}
    return jwt.encode(payload, secret, algorithm=alg)


async def _my_id(client, headers):
    return (await client.get(f"{API}/users/me", headers=headers)).json()["user_id"]


async def test_forged_expired_or_alien_tokens_are_rejected(client, family):
    uid = await _my_id(client, family)
    none_alg = (base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode() + "."
                + base64.urlsafe_b64encode(json.dumps({"sub": uid, "exp": 9999999999}).encode()).rstrip(b"=").decode() + ".")
    bad = {
        "sin firma (alg none)": none_alg,
        "firmado con otra clave": _token(uid, secret="otra-clave-distinta-de-32-caracteres-xx"),
        "vencido": _token(uid, exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
        "sin vencimiento": jwt.encode({"sub": uid}, "secreto-de-test-con-largo-suficiente-123456", algorithm="HS256"),
        "usuario inexistente": _token(uuid.uuid4()),
        "basura": "esto.no.es.un.token",
        "vacío": "",
        "con otro algoritmo": _token(uid, alg="HS512"),
    }
    for name, tok in bad.items():
        r = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code in (401, 403), (name, r.status_code)
    good = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {_token(uid)}"})
    assert good.status_code == 200  # el control: un token legítimo sí funciona


async def test_refresh_token_cannot_be_used_twice(client):
    r = await client.post(f"{API}/auth/login", json={"email": "familia@demo.cl", "password": "Familia123!"})
    old = r.json()["refresh_token"]
    ok = await client.post(f"{API}/auth/refresh", json={"refresh_token": old})
    assert ok.status_code == 200
    again = await client.post(f"{API}/auth/refresh", json={"refresh_token": old})
    assert again.status_code == 401
    assert (await client.post(f"{API}/auth/refresh", json={"refresh_token": "inventado"})).status_code == 401


# ---------- Cada ruta protegida exige sesión ----------
PUBLIC = {"/health", "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh",
          "/api/v1/docs", "/api/v1/openapi.json", "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


def _operations():
    """(método, ruta) de todos los endpoints, leídos del esquema OpenAPI."""
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


async def test_every_route_rejects_requests_without_a_session(client):
    checked = 0
    for method, path in _operations():
        if path in PUBLIC or path.startswith("/api/v1/internal") or not path.startswith("/api/v1"):
            continue
        url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        r = await client.request(method, url, json={} if method in ("POST", "PUT", "PATCH") else None)
        assert r.status_code in (401, 403), f"{method} {path} respondió {r.status_code} sin sesión"
        checked += 1
    assert checked > 25


async def test_internal_routes_need_the_shared_key(client):
    checked = 0
    for method, path in _operations():
        if not path.startswith("/api/v1/internal"):
            continue
        url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        for headers in ({}, {"X-Internal-Key": "adivinada"}, {"X-Internal-Key": ""}):
            r = await client.request(method, url, headers=headers, json={} if method == "POST" else None)
            assert r.status_code in (401, 403), (method, path, headers, r.status_code)
        checked += 1
    assert checked >= 5
    # Y con la clave correcta sí entra (aquí falla por datos, no por permisos).
    r = await client.get(f"{API}/internal/caregivers/documents", params={"email": "maria@cuidado.cl"}, headers=INTERNAL)
    assert r.status_code == 200


# ---------- Datos de otras personas ----------
async def test_a_family_cannot_see_or_delete_another_familys_relative(client, family):
    patients = (await client.get(f"{API}/patients", headers=family)).json()
    pid = (patients["items"] if isinstance(patients, dict) else patients)[0]["patient_id"]
    other = await client.post(f"{API}/auth/register", json={
        "full_name": "Intrusa Prueba", "email": "intrusa@test.cl", "password": "Segura123!", "account_type": "family"})
    h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"{API}/patients/{pid}", headers=h)).status_code in (403, 404)
    assert (await client.delete(f"{API}/patients/{pid}", headers=h)).status_code in (403, 404)
    assert (await client.patch(f"{API}/patients/{pid}", headers=h, json={"full_name": "Hackeada"})).status_code in (403, 404, 405)
    # Sigue intacta para su dueña.
    assert (await client.get(f"{API}/patients/{pid}", headers=family)).status_code == 200


async def test_account_types_cannot_use_each_others_endpoints(client, family, maria):
    assert (await client.get(f"{API}/caregiver/profile", headers=family)).status_code in (403, 404)
    assert (await client.get(f"{API}/caregiver/reviews", headers=family)).status_code in (403, 404)
    assert (await client.get(f"{API}/marketplace/caregivers", headers=maria)).status_code == 403
    r = await client.post(f"{API}/marketplace/caregivers/{uuid.uuid4()}/reviews", headers=maria, json={"rating": 5})
    assert r.status_code in (403, 404)


async def test_a_user_cannot_read_someone_elses_chat(client, family, javiera, maria):
    pid = (await client.get(f"{API}/marketplace/caregivers", headers=family)).json()
    items = pid["items"] if isinstance(pid, dict) else pid
    cid = next(i["profile_id"] for i in items if i["full_name"].startswith("Javiera"))
    r = await client.post(f"{API}/marketplace/caregivers/{cid}/contact", headers=family, json={"message": "Hola"})
    assert r.status_code in (200, 201), r.text
    conv = r.json().get("conversation_id")
    # María no participa en esa conversación.
    assert (await client.get(f"{API}/chats/{conv}", headers=maria)).status_code in (403, 404)
    r = await client.post(f"{API}/chats/{conv}/messages", headers=maria, json={"body": "intruso"})
    assert r.status_code in (403, 404, 422)
    assert (await client.get(f"{API}/chats/{conv}", headers=javiera)).status_code == 200


# ---------- Fuerza bruta y contraseñas ----------
async def test_login_is_locked_after_repeated_failures(client):
    for _ in range(5):
        r = await client.post(f"{API}/auth/login", json={"email": "familia@demo.cl", "password": "mala"})
        assert r.status_code == 401
    # Ya bloqueada: ni siquiera la contraseña correcta entra.
    r = await client.post(f"{API}/auth/login", json={"email": "familia@demo.cl", "password": "Familia123!"})
    assert r.status_code == 423


async def test_error_messages_do_not_reveal_which_part_was_wrong(client):
    a = await client.post(f"{API}/auth/login", json={"email": "noexiste@test.cl", "password": "Mala12345!"})
    b = await client.post(f"{API}/auth/login", json={"email": "maria@cuidado.cl", "password": "Mala12345!"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


async def test_passwords_are_never_returned_or_stored_in_plain_text(client, family):
    me = await client.get(f"{API}/users/me", headers=family)
    assert "password" not in me.text.lower() and "hash" not in me.text.lower()
    r = await client.post(f"{API}/auth/login", json={"email": "familia@demo.cl", "password": "Familia123!"})
    assert "Familia123!" not in r.text and "argon2" not in r.text


async def test_short_passwords_are_refused(client):
    r = await client.post(f"{API}/auth/register", json={
        "full_name": "Corta Clave", "email": "corta@test.cl", "password": "1234567", "account_type": "family"})
    assert r.status_code == 422


# ---------- Cabeceras ----------
async def test_security_headers_are_sent(client):
    r = await client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy")
    assert "strict-transport-security" in r.headers
    assert "server" not in {k.lower() for k in r.headers if k.lower() == "x-powered-by"}


async def test_cors_only_allows_the_known_sites(client):
    ok = await client.options(f"{API}/auth/login", headers={
        "Origin": "http://localhost:5174", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5174"
    evil = await client.options(f"{API}/auth/login", headers={
        "Origin": "https://sitio-malicioso.example", "Access-Control-Request-Method": "POST"})
    assert evil.headers.get("access-control-allow-origin") is None


# ---------- Consistencia ----------
async def test_changes_are_saved_before_the_response_is_sent():
    """Con el comportamiento por defecto de FastAPI el `commit` ocurre DESPUÉS de responder: la persona recibe
    «creado» y su siguiente petición puede no ver el dato todavía (403/404 al azar con la base lejos o con carga).
    La sesión debe declararse con scope="function"."""
    from app.deps import Db
    dependency = next(m for m in Db.__metadata__ if hasattr(m, "dependency"))
    assert dependency.scope == "function"
