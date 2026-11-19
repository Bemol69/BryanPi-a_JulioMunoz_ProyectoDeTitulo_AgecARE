"""Flujos en vivo (solo HTTP, sin navegador) que recorren las dos APIs y, después de CADA acción, comprueban que el
sitio y la Consola sigan mostrando lo mismo (pruebas/consistencia.py).

Cubre: registro y perfil de una cuidadora, documentos, aprobación y cobro, foto, cambios de perfil, contratación,
reseñas, puntos, archivar/restaurar/eliminar reseñas, suspender y reactivar, cambiar el cobro, y borrar la cuenta
(desde la Consola y desde el sitio).

Uso (con las dos APIs levantadas y sincronizadas entre sí, datos de demostración recién sembrados):
    python e2e/flujos_consistencia.py
Crea cuentas de prueba: solo para ambientes de prueba, nunca contra producción.
"""
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("consistencia", ROOT / "pruebas" / "consistencia.py")
consistencia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consistencia)

SITE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/api/v1"
CON = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000/api/v1/admin"
PNG = bytes.fromhex("89504e470d0a1a0a") + b"imagen-de-prueba-" + b"x" * 200
TAG = uuid.uuid4().hex[:6]
PW = "Prueba12345!"
RESULTS = []


def req(base, method, path, token=None, body=None, files=None, form=None, ok=(200, 201, 204)):
    headers = {"Authorization": "Bearer " + token} if token else {}
    data = None
    if files is not None:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (form or {}).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (fn, content, ctype) in files.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                         + content + b"\r\n")
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(base + path, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode(errors="replace")[:200]


def site(method, path, token=None, **kw):
    st, data = req(SITE, method, path, token, **kw)
    assert st in (200, 201, 204), f"SITIO {method} {path} -> {st} {str(data)[:160]}"
    return data


def con(method, path, token=None, **kw):
    st, data = req(CON, method, path, token, **kw)
    assert st in (200, 201, 204), f"CONSOLA {method} {path} -> {st} {str(data)[:160]}"
    return data


def login(base, email, pw):
    return req(base, "POST", "/auth/login", body={"email": email, "password": pw})[1]["access_token"]


def register(kind, name, email):
    return site("POST", "/auth/register", body={"full_name": name, "email": email, "password": PW, "account_type": kind})["access_token"]


def checkpoint(name, extra=None):
    """Corre el verificador y además las comprobaciones propias del paso."""
    problems = []
    try:
        if extra:
            extra()
    except AssertionError as e:
        problems.append(str(e))
    checks, diffs = consistencia.verificar(SITE, CON, verbose=False)
    problems += diffs
    RESULTS.append((name, checks, problems))
    print(("OK   " if not problems else "FALLA"), name, f"({checks} comprobaciones)")
    for p in problems:
        print("      ✗", p)


admin = login(CON, "admin@wellq.co.uk", "Admin123!")
fam_demo = login(SITE, "familia@demo.cl", "Familia123!")
checkpoint("0. Datos de demostración recién cargados")


def console_row(name):
    items = con("GET", f"/marketplace/caregivers?q={urllib.parse.quote(name)}&page_size=50", admin)["items"]
    return next((i for i in items if i["name"] == name), None)


import urllib.parse  # noqa: E402

# ---------------------------------------------------------------- 1. La cuidadora se une
NAME = f"Valentina Prueba {TAG}"
EMAIL = f"valentina.{TAG}@cuidado.cl"
cg = register("caregiver", NAME, EMAIL)
site("PUT", "/caregiver/profile", cg, body={
    "headline": "Cuidadora de prueba", "bio": "Experiencia en acompañamiento de adultos mayores con paciencia y respeto.",
    "years_experience": 5, "specialties": ["Alzheimer", "Posoperatorio"], "languages": ["Español", "Inglés"],
    "zones": ["Ñuñoa", "Providencia"], "is_listed": True})


def after_profile():
    row = console_row(NAME)
    assert row is not None, "la cuidadora que se registró en el sitio NO llegó a la Consola"
    assert row["status"] == "pending", f"debería llegar «pendiente» y llegó «{row['status']}»"
    assert set(row["specialties"]) == {"Alzheimer", "Posoperatorio"}, f"especialidades en la Consola: {row['specialties']}"
    assert set(row["languages"]) == {"Español", "Inglés"}, f"idiomas en la Consola: {row['languages']}"
    assert row["zone"] == "Ñuñoa", f"zona en la Consola: {row['zone']}"
    names = {c["full_name"] for c in consistencia.all_pages(SITE, "/marketplace/caregivers", fam_demo)}
    assert NAME not in names, "una cuidadora SIN aprobar aparece en las búsquedas de las familias"


checkpoint("1. La cuidadora se registra y completa su perfil (llega pendiente, no se ve en el sitio)", after_profile)

# ---------------------------------------------------------------- 2. Documentos
for t in ("id_card", "background_check", "certificate"):
    site("POST", "/caregiver/documents", cg, files={"file": (f"{t}.png", PNG, "image/png")}, form={"doc_type": t})


def after_docs():
    row = console_row(NAME)
    d = con("GET", f"/marketplace/caregivers/{row['caregiver_id']}", admin)
    assert len(d["documents"]) == 3 and d["pending_documents"] == 3, f"documentos en la Consola: {len(d['documents'])} / pendientes {d['pending_documents']}"


checkpoint("2. Sube cédula, antecedentes y certificado (quedan pendientes en la Consola)", after_docs)

# ---------------------------------------------------------------- 3. El staff aprueba
cid = console_row(NAME)["caregiver_id"]
for t in ("id_card", "background_check", "certificate"):
    con("POST", f"/marketplace/caregivers/{cid}/documents/{t}/review", admin, body={"action": "approve"})


def after_docs_ok():
    st = {d["doc_type"]: d["status"] for d in site("GET", "/caregiver/documents", cg)}
    assert set(st.values()) == {"approved"}, f"la cuidadora ve sus documentos así en el sitio: {st}"


checkpoint("3. El staff aprueba los 3 documentos (la cuidadora los ve «aprobados» en el sitio)", after_docs_ok)

con("POST", f"/marketplace/caregivers/{cid}/verification", admin, body={"action": "paid", "method": "transfer", "receipt": f"TR-{TAG}"})
con("PATCH", f"/marketplace/caregivers/{cid}", admin, body={"status": "approved"})
pid = site("GET", "/caregiver/profile", cg)["profile_id"]


def after_approve():
    names = {c["full_name"]: c for c in consistencia.all_pages(SITE, "/marketplace/caregivers", fam_demo)}
    assert NAME in names, "aprobada en la Consola pero NO aparece en el sitio"
    assert names[NAME]["is_qualified"] is True, "pagó la verificación pero el sitio no le da la insignia «calificado»"


checkpoint("4. Cobro de verificación confirmado y perfil aprobado (aparece en el sitio, con insignia)", after_approve)

# ---------------------------------------------------------------- 5. Foto
site("POST", "/users/me/avatar", cg, files={"file": ("foto.png", PNG, "image/png")})
checkpoint("5. La cuidadora sube su foto (debe verse igual en la Consola)")

# ---------------------------------------------------------------- 6. Cambios de perfil
site("PUT", "/caregiver/profile", cg, body={"specialties": ["Demencia"], "languages": ["Español"], "zones": ["Maipú"]})
checkpoint("6. Cambia sus especialidades, idiomas y zona (la Consola debe actualizarse)")

# ---------------------------------------------------------------- 7. Contratación
fam = register("family", f"Familia Prueba {TAG}", f"familia.{TAG}@prueba.cl")
patient = site("POST", "/patients", fam, body={"full_name": "Abuela de Prueba", "birth_date": "1945-05-05"})["patient_id"]
hire = site("POST", f"/marketplace/caregivers/{pid}/hire-requests", fam, body={"patient_id": patient, "message": "Hola"})
reqs = site("GET", "/caregiver/hire-requests", cg)["items"]
eng = site("POST", f"/caregiver/hire-requests/{reqs[0]['request_id']}/accept", cg)
checkpoint("7. Una familia la contrata y ella acepta (debe figurar «trabajando» en los dos lados)",
           lambda: (_ for _ in ()).throw(AssertionError("la Consola no la muestra «trabajando»")) if not console_row(NAME)["is_engaged"] else None)

# ---------------------------------------------------------------- 8. Reseñas
site("POST", f"/marketplace/engagements/{eng['engagement_id']}/end", fam)
site("POST", f"/marketplace/caregivers/{pid}/reviews", fam, body={"rating": 2, "comment": "Llegó tarde.", "patient_id": patient})


def after_review():
    row = console_row(NAME)
    assert row["reviews_count"] == 1 and row["rating_avg"] == 2.0, f"Consola: {row['reviews_count']} reseñas, nota {row['rating_avg']}"
    assert not row["is_engaged"], "terminó el trabajo y la Consola la sigue mostrando «trabajando»"
    rank = con("GET", "/marketplace/caregivers/ranking?page_size=100", admin)["items"]
    pts = next(i["points"] for i in rank if i["name"] == NAME)
    assert pts == 5, f"una reseña de 2 estrellas debería dejar 5 puntos netos (10 - 5) y dejó {pts}"


checkpoint("8. Fin del trabajo y reseña de 2 estrellas (nota, conteo, «trabajando» y puntos)", after_review)

# ---------------------------------------------------------------- 9. Moderación
rid = con("GET", f"/marketplace/caregivers/{cid}/reviews", admin)["items"][0]["id"]
con("PATCH", f"/marketplace/reviews/{rid}", admin, body={"archived": True})


def after_archive():
    d = site("GET", f"/marketplace/caregivers/{pid}", fam_demo)
    assert d["reviews_count"] == 0 and d["reviews"] == [], f"archivada en la Consola pero el sitio aún muestra {d['reviews_count']} reseñas"
    assert console_row(NAME)["reviews_count"] == 0


checkpoint("9. El staff ARCHIVA la reseña (el sitio la oculta y recalcula la nota)", after_archive)
con("PATCH", f"/marketplace/reviews/{rid}", admin, body={"archived": False})
checkpoint("10. El staff la RESTAURA (vuelve a verse y a contar)",
           lambda: (_ for _ in ()).throw(AssertionError("restaurada pero el sitio no la muestra")) if site("GET", f"/marketplace/caregivers/{pid}", fam_demo)["reviews_count"] != 1 else None)
con("DELETE", f"/marketplace/reviews/{rid}", admin)
checkpoint("11. El staff ELIMINA la reseña (desaparece de los dos lados)",
           lambda: (_ for _ in ()).throw(AssertionError("eliminada pero el sitio aún la muestra")) if site("GET", f"/marketplace/caregivers/{pid}", fam_demo)["reviews_count"] != 0 else None)

# ---------------------------------------------------------------- 12. Suspender y reactivar
con("PATCH", f"/marketplace/caregivers/{cid}", admin, body={"status": "suspended", "reason": "Reiteradas ausencias reportadas"})
checkpoint("12. El staff la SUSPENDE (desaparece de las búsquedas)",
           lambda: (_ for _ in ()).throw(AssertionError("suspendida pero sigue en las búsquedas")) if NAME in {c["full_name"] for c in consistencia.all_pages(SITE, "/marketplace/caregivers", fam_demo)} else None)
con("PATCH", f"/marketplace/caregivers/{cid}", admin, body={"status": "approved"})
checkpoint("13. El staff la REACTIVA (vuelve a aparecer)")

# ---------------------------------------------------------------- 14. Cobro
con("POST", f"/marketplace/caregivers/{cid}/verification", admin, body={"action": "waived", "reason": "launch_promo", "days": 30, "note": "Prueba"})
checkpoint("14. Se le EXIME el pago (sigue publicada pero sin insignia «calificado»)",
           lambda: (_ for _ in ()).throw(AssertionError("eximida pero conserva la insignia")) if next(c for c in consistencia.all_pages(SITE, "/marketplace/caregivers", fam_demo) if c["full_name"] == NAME)["is_qualified"] else None)
con("POST", f"/marketplace/caregivers/{cid}/verification", admin, body={"action": "paid", "method": "cash", "receipt": f"EF-{TAG}"})
checkpoint("15. Vuelve a pagar (recupera la insignia)")

# ---------------------------------------------------------------- 16. Borrados
con("DELETE", f"/marketplace/caregivers/{cid}", admin)


def after_delete():
    assert console_row(NAME) is None, "eliminada y sigue en la Consola"
    assert req(SITE, "POST", "/auth/login", body={"email": EMAIL, "password": PW})[0] == 401, "eliminada desde la Consola pero su cuenta del sitio sigue activa"


checkpoint("16. El staff ELIMINA su perfil (se va la cuenta del sitio y todo su rastro)", after_delete)

NAME2, EMAIL2 = f"Camila Prueba {TAG}", f"camila.{TAG}@cuidado.cl"
cg2 = register("caregiver", NAME2, EMAIL2)
site("PUT", "/caregiver/profile", cg2, body={"headline": "Otra de prueba", "bio": "Cuidadora con experiencia y mucha paciencia para acompañar.",
                                              "years_experience": 2, "specialties": ["Acompañamiento"], "languages": ["Español"], "zones": ["Maipú"], "is_listed": True})
assert console_row(NAME2) is not None, "la segunda cuidadora no llegó a la Consola"
site("DELETE", "/users/me", cg2, body={"password": PW})
checkpoint("17. La cuidadora BORRA su cuenta en el sitio (desaparece de la Consola)",
           lambda: (_ for _ in ()).throw(AssertionError("borró su cuenta y sigue en la Consola")) if console_row(NAME2) is not None else None)

bad = [r for r in RESULTS if r[2]]
print(f"\nRESUMEN: {len(RESULTS) - len(bad)} de {len(RESULTS)} puntos de control sin diferencias")
sys.exit(1 if bad else 0)
