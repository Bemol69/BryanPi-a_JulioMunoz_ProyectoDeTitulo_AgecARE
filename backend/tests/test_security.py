"""Seguridad de la Consola de administración: inyección SQL, tokens falsos, permisos por rol,
clave interna, fuerza bruta y cabeceras. Nada de esto debe dar 200 ni un error 500."""
import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import get_settings
from app.main import app

BASE = "/api/v1/admin"
INTERNAL = {"X-Internal-Key": "clave-interna-solo-para-desarrollo"}
SQLI = [
    "' OR '1'='1",
    "' OR 1=1--",
    "admin'--",
    "'; DROP TABLE admin_users;--",
    "\" OR \"\"=\"",
    "' UNION SELECT password_hash FROM admin_users--",
    "1; SELECT pg_sleep(5)--",
]


async def _new_staff(role: str) -> str:
    from app import models
    from app.database import get_session_factory
    from app.security import hash_password
    email = f"{role}{uuid.uuid4().hex[:8]}@wellq.co.uk"
    async with get_session_factory()() as db:
        db.add(models.AdminUser(full_name="Cuenta de prueba", email=email, role=role,
                                password_hash=hash_password("Victima123!"), is_active=True))
        await db.commit()
    return email


@pytest.fixture
async def victim(client):
    """Cuenta nueva para cada prueba que falla contraseñas a propósito: así no bloquea a las demás."""
    return await _new_staff("analyst")


def _operations():
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


# ---------- Inyección SQL ----------
@pytest.mark.parametrize("payload", SQLI)
async def test_sql_injection_in_login_never_logs_in(client, victim, payload):
    r = await client.post(f"{BASE}/auth/login", json={"email": payload, "password": "x"})
    assert r.status_code in (401, 422) and "access_token" not in r.text
    r = await client.post(f"{BASE}/auth/login", json={"email": victim, "password": payload})
    assert r.status_code == 401 and "access_token" not in r.text


@pytest.mark.parametrize("payload", SQLI)
async def test_sql_injection_in_filters_returns_normal_results(client, admin_headers, payload):
    for path, key in (("/marketplace/caregivers", "q"), ("/marketplace/caregivers", "zone"),
                      ("/marketplace/caregivers/ranking", "zone"), ("/marketplace/products", "q"),
                      ("/marketplace/products", "category")):
        r = await client.get(f"{BASE}{path}", params={key: payload}, headers=admin_headers)
        assert r.status_code in (200, 422), (path, key, r.status_code, r.text[:160])
    # Las tablas siguen intactas.
    assert (await client.get(f"{BASE}/auth/me", headers=admin_headers)).status_code == 200


@pytest.mark.parametrize("payload", SQLI[:4])
async def test_sql_injection_in_ids_is_rejected(client, admin_headers, payload):
    r = await client.get(f"{BASE}/marketplace/caregivers/{payload}", headers=admin_headers)
    assert r.status_code in (404, 422)


async def test_sql_text_in_a_caregiver_profile_is_stored_as_plain_text(client, admin_headers):
    r = await client.post(f"{BASE}/marketplace/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": "x", "name": "Eva'; DROP TABLE marketplace_caregivers;--", "email": "sqli@test.cl",
        "zone": "' OR 1=1--", "specialties": ["<script>alert(1)</script>"], "languages": [], "certifications_count": 0})
    assert r.status_code in (200, 201), r.text
    got = (await client.get(f"{BASE}/marketplace/caregivers/{r.json()['caregiver_id']}", headers=admin_headers)).json()
    assert got["name"] == "Eva'; DROP TABLE marketplace_caregivers;--"
    assert (await client.get(f"{BASE}/marketplace/caregivers", headers=admin_headers)).status_code == 200


# ---------- Tokens ----------
def _token(sub, role="admin", secret=None, alg="HS256", exp=None):
    s = get_settings()
    payload = {"sub": str(sub), "role": role, "type": "access",
               "exp": exp or datetime.now(timezone.utc) + timedelta(minutes=10)}
    return jwt.encode(payload, secret or s.jwt_secret, algorithm=alg)


async def test_forged_expired_or_alien_tokens_are_rejected(client, admin_headers):
    me = (await client.get(f"{BASE}/auth/me", headers=admin_headers)).json()
    uid = me.get("admin_id") or me.get("id") or me.get("user_id")
    none_alg = (base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode() + "."
                + base64.urlsafe_b64encode(json.dumps({"sub": str(uid), "role": "admin", "exp": 9999999999}).encode()).rstrip(b"=").decode() + ".")
    bad = {
        "sin firma (alg none)": none_alg,
        "firmado con otra clave": _token(uid, secret="otra-clave-distinta-de-32-caracteres-xx"),
        "vencido": _token(uid, exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
        "usuario inexistente": _token(uuid.uuid4()),
        "basura": "esto.no.es.un.token",
        "con otro algoritmo": _token(uid, alg="HS512"),
    }
    for name, tok in bad.items():
        r = await client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code in (401, 403), (name, r.status_code)
    assert (await client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {_token(uid)}"})).status_code == 200


async def test_a_token_cannot_raise_its_own_role(client, analyst_headers):
    """El rol sale de la base de datos, no del token: un analista no se vuelve admin editando el token."""
    me = (await client.get(f"{BASE}/auth/me", headers=analyst_headers)).json()
    uid = me.get("admin_id") or me.get("id") or me.get("user_id")
    forged = {"Authorization": f"Bearer {_token(uid, role='admin')}"}
    r = await client.post(f"{BASE}/marketplace/reviews", headers=forged,
                          json={"caregiver_id": str(uuid.uuid4()), "family_name": "Hacker", "rating": 5})
    assert r.status_code in (403, 404)


# ---------- Cada ruta exige sesión ----------
PUBLIC = {f"{BASE}/auth/login", f"{BASE}/auth/refresh", f"{BASE}/docs", f"{BASE}/openapi.json", "/health"}


async def test_every_route_rejects_requests_without_a_session(client):
    checked = 0
    for method, path in _operations():
        if path in PUBLIC or not path.startswith(BASE):
            continue
        url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        keyed = {"/marketplace/caregivers/sync", "/marketplace/caregivers/remove",
                 "/marketplace/documents/sync", "/marketplace/reviews/sync", "/marketplace/caregivers/statuses"}
        r = await client.request(method, url, json={} if method in ("POST", "PUT", "PATCH") else None)
        assert r.status_code in (401, 403), f"{method} {path} respondió {r.status_code} sin sesión"
        checked += 1
    assert checked > 30


async def test_internal_routes_need_the_shared_key(client):
    internal = [(m, p) for m, p in _operations()
                if p.startswith(f"{BASE}/marketplace") and any(p.endswith(x) for x in
                   ("/caregivers/sync", "/caregivers/remove", "/documents/sync", "/reviews/sync", "/statuses"))]
    assert len(internal) >= 5
    for method, path in internal:
        for headers in ({}, {"X-Internal-Key": "adivinada"}):
            r = await client.request(method, path, headers=headers, json={} if method == "POST" else None)
            assert r.status_code in (401, 403), (method, path, headers, r.status_code)


# ---------- Permisos por rol ----------
async def test_read_only_staff_cannot_change_anything(client, analyst_headers, admin_headers):
    moderator = await _new_staff("moderator")
    r = await client.post(f"{BASE}/auth/login", json={"email": moderator, "password": "Victima123!"})
    mod_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    cid = (await client.post(f"{BASE}/marketplace/caregivers/sync", headers=INTERNAL, json={
        "external_user_id": "ro", "name": "Solo Lectura", "email": "ro@test.cl", "zone": "Providencia",
        "specialties": [], "languages": [], "certifications_count": 0})).json()["caregiver_id"]
    writes = [
        ("PATCH", f"/marketplace/caregivers/{cid}", {"status": "suspended", "reason": "no debería poder hacerlo"}),
        ("DELETE", f"/marketplace/caregivers/{cid}", None),
        ("POST", f"/marketplace/caregivers/{cid}/points", {"points": 50, "reason": "manual"}),
        ("POST", "/marketplace/reviews", {"caregiver_id": cid, "family_name": "Familia", "rating": 5}),
        ("DELETE", f"/marketplace/reviews/{uuid.uuid4()}", None),
        ("PATCH", f"/marketplace/reviews/{uuid.uuid4()}", {"archived": True}),
    ]
    for headers in (analyst_headers, mod_headers):  # el analista ni lee el Marketplace; el moderador solo lee
        for method, path, body in writes:
            r = await client.request(method, f"{BASE}{path}", headers=headers, json=body)
            assert r.status_code == 403, (method, path, r.status_code)
    assert (await client.get(f"{BASE}/marketplace/caregivers/{cid}", headers=mod_headers)).status_code == 200
    assert (await client.get(f"{BASE}/marketplace/caregivers/{cid}", headers=analyst_headers)).status_code == 403
    assert (await client.get(f"{BASE}/marketplace/caregivers/{cid}", headers=admin_headers)).json()["status"] == "pending"


# ---------- Fuerza bruta ----------
async def test_login_is_locked_after_repeated_failures(client, victim):
    for _ in range(5):
        r = await client.post(f"{BASE}/auth/login", json={"email": victim, "password": "mala-clave"})
        assert r.status_code == 401
    r = await client.post(f"{BASE}/auth/login", json={"email": victim, "password": "Victima123!"})
    assert r.status_code == 423


async def test_error_messages_do_not_reveal_which_part_was_wrong(client):
    a = await client.post(f"{BASE}/auth/login", json={"email": "noexiste@wellq.co.uk", "password": "Mala12345!"})
    b = await client.post(f"{BASE}/auth/login", json={"email": "admin@wellq.co.uk", "password": "Mala12345!"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


async def test_passwords_are_never_returned(client, admin_headers):
    me = await client.get(f"{BASE}/auth/me", headers=admin_headers)
    assert "password" not in me.text.lower() and "mfa_secret" not in me.text.lower()


# ---------- Cabeceras y CORS ----------
async def test_security_headers_and_cors(client):
    r = await client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "strict-transport-security" in r.headers
    ok = await client.options(f"{BASE}/auth/login", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    evil = await client.options(f"{BASE}/auth/login", headers={
        "Origin": "https://sitio-malicioso.example", "Access-Control-Request-Method": "POST"})
    assert evil.headers.get("access-control-allow-origin") is None


async def test_changes_are_saved_before_the_response_is_sent():
    """Ver la misma prueba del sitio público: el `commit` debe ocurrir antes de responder."""
    from app.deps import Db
    dependency = next(m for m in Db.__metadata__ if hasattr(m, "dependency"))
    assert dependency.scope == "function"
