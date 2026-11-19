"""Compara lo que muestra el sitio público con lo que muestra la Consola (solo lectura, solo librería estándar).

Detecta cosas como: una cuidadora que aparece en las búsquedas y no existe en la Consola, una con 4,7 estrellas
en un lado y sin reseñas en el otro, fotos, idiomas o precios distintos, o artículos que no coinciden.

Uso (con las dos APIs levantadas):
    python pruebas/consistencia.py
    python pruebas/consistencia.py --sitio https://agecare-api-general.vercel.app/api/v1 \\
        --consola https://bryan-pi-a-julio-munoz-proyecto-de.vercel.app/api/v1/admin

Solo inicia sesión y consulta (GET). Termina con código 1 si encuentra diferencias.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")


def call(base, path, token=None, body=None):
    req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{e.code} en {path}: {e.read()[:200]!r}")


def all_pages(base, path, token):
    items, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        data = call(base, f"{path}{sep}page={page}&page_size=100", token)
        items += data["items"]
        if len(items) >= data["total"] or not data["items"]:
            return items
        page += 1


def verificar(sitio, consola, familia="familia@demo.cl:Familia123!", admin="admin@wellq.co.uk:Admin123!", verbose=True):
    """Devuelve (comprobaciones, lista de diferencias)."""
    fe, fp = familia.split(":", 1)
    ae, ap_ = admin.split(":", 1)
    a = argparse.Namespace(sitio=sitio, consola=consola)
    site_tok = call(a.sitio, "/auth/login", body={"email": fe, "password": fp})["access_token"]
    con_tok = call(a.consola, "/auth/login", body={"email": ae, "password": ap_})["access_token"]

    site = {c["full_name"]: c for c in all_pages(a.sitio, "/marketplace/caregivers", site_tok)}
    con = {c["name"]: c for c in all_pages(a.consola, "/marketplace/caregivers", con_tok)}
    problems: list[str] = []
    checks = 0

    def check(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            problems.append(msg)

    # 1. Las mismas personas: todo lo aprobado en la Consola se ve en el sitio y viceversa.
    approved = {n for n, c in con.items() if c["status"] == "approved"}
    for n in sorted(set(site) - set(con)):
        check(False, f"«{n}» aparece en las búsquedas del sitio pero NO existe en la Consola")
    for n in sorted(approved - set(site)):
        # Una exención vencida la oculta a propósito.
        if not con[n].get("verification_waiver_expired"):
            check(False, f"«{n}» está aprobada en la Consola pero NO aparece en el sitio")
    for n in sorted(set(site) & set(con)):
        check(con[n]["status"] == "approved", f"«{n}» se ve en el sitio pero en la Consola está «{con[n]['status']}»")

    # 2. Cada dato de las que están en los dos lados.
    for n in sorted(set(site) & set(con)):
        s, c = site[n], con[n]
        detail = call(a.sitio, f"/marketplace/caregivers/{s['profile_id']}", site_tok)
        check(s["photo_url"] == c.get("photo_url"), f"«{n}»: foto distinta (sitio {s['photo_url']} / Consola {c.get('photo_url')})")
        check(set(s["specialties"]) == set(c["specialties"]), f"«{n}»: especialidades distintas ({s['specialties']} / {c['specialties']})")
        check(set(detail["languages"]) == set(c["languages"]), f"«{n}»: idiomas distintos ({detail['languages']} / {c['languages']})")
        check(bool(s["zones"]) and s["zones"][0] == c["zone"], f"«{n}»: zona distinta ({s['zones']} / {c['zone']})")
        check(s["is_engaged"] == c["is_engaged"], f"«{n}»: «trabajando» distinto (sitio {s['is_engaged']} / Consola {c['is_engaged']})")
        check(s["is_qualified"] == (c["verification_fee_status"] == "paid"),
              f"«{n}»: insignia «calificado» del sitio ({s['is_qualified']}) no corresponde al pago en la Consola ({c['verification_fee_status']})")
        # Reseñas: lo que dice la ficha, lo que dice el listado y lo que dice la Consola deben coincidir.
        shown = detail["reviews"]
        check(len(shown) == s["reviews_count"], f"«{n}»: el sitio dice {s['reviews_count']} reseñas pero su ficha lista {len(shown)}")
        if shown:
            check(abs(mean(r["rating"] for r in shown) - s["rating_avg"]) < 0.011,
                  f"«{n}»: la nota del sitio ({s['rating_avg']}) no es el promedio de sus reseñas ({mean(r['rating'] for r in shown):.2f})")
        check(s["reviews_count"] == c["reviews_count"], f"«{n}»: {s['reviews_count']} reseñas en el sitio y {c['reviews_count']} en la Consola")
        check((s["rating_avg"] or 0) == (c["rating_avg"] or 0), f"«{n}»: nota {s['rating_avg']} en el sitio y {c['rating_avg']} en la Consola")
        cr = all_pages(a.consola, f"/marketplace/caregivers/{c['caregiver_id']}/reviews", con_tok)
        live = [r for r in cr if not r.get("archived_at")]
        check(len(live) == c["reviews_count"], f"«{n}»: la Consola dice {c['reviews_count']} reseñas pero lista {len(live)} vigentes")
        if live:
            check(abs(mean(r["rating"] for r in live) - (c["rating_avg"] or 0)) < 0.011,
                  f"«{n}»: la nota de la Consola ({c['rating_avg']}) no es el promedio de sus reseñas")

    # 3. Artículos de apoyo.
    site_p = {p["name"]: p for p in all_pages(a.sitio, "/marketplace/products", site_tok)}
    con_p = {p["name"]: p for p in all_pages(a.consola, "/marketplace/products", con_tok)}
    for n in sorted(set(site_p) - set(con_p)):
        check(False, f"Artículo «{n}»: está en el sitio y no en la Consola")
    for n in sorted(n for n, p in con_p.items() if p["status"] == "published" and n not in site_p):
        check(False, f"Artículo «{n}»: está publicado en la Consola y no se ve en el sitio")
    for n in sorted(set(site_p) & set(con_p)):
        s, c = site_p[n], con_p[n]
        check(s["price_clp"] == c["price_clp"], f"Artículo «{n}»: precio {s['price_clp']} en el sitio y {c['price_clp']} en la Consola")
        check(s["vendor"] == c["vendor"], f"Artículo «{n}»: proveedor distinto ({s['vendor']} / {c['vendor']})")
        check(bool(s["is_sponsored"]) == bool(c["is_sponsored"]), f"Artículo «{n}»: patrocinio distinto")
        check(s["product_id"] == c["id"], f"Artículo «{n}»: no tiene el mismo identificador en los dos sistemas")

    if verbose:
        print(f"Sitio: {len(site)} cuidadoras visibles, {len(site_p)} artículos · Consola: {len(con)} cuidadoras "
              f"({len(approved)} aprobadas), {len(con_p)} artículos")
    return checks, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sitio", default="http://127.0.0.1:8001/api/v1")
    ap.add_argument("--consola", default="http://127.0.0.1:8000/api/v1/admin")
    ap.add_argument("--familia", default="familia@demo.cl:Familia123!")
    ap.add_argument("--admin", default="admin@wellq.co.uk:Admin123!")
    a = ap.parse_args()
    checks, problems = verificar(a.sitio, a.consola, a.familia, a.admin)
    print(f"{checks} comprobaciones, {len(problems)} diferencias")
    for p in problems:
        print("  ✗", p)
    if not problems:
        print("  ✓ El sitio y la Consola muestran lo mismo")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
