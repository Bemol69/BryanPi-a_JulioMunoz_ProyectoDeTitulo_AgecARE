"""Recorrido de punta a punta con la interfaz real de AgeCare (sitio y Consola).

Registra cuentas nuevas, completa un perfil de cuidador, sube foto y documentos, los aprueba desde la Consola,
contrata, conversa por el chat y deja una reseña, comprobando el resultado en cada paso.

Requisitos: `pip install playwright` y Google Chrome instalado. Las dos webs y las dos APIs deben estar en marcha
con los datos de demostración (ver README). Uso:  python e2e/run_e2e.py
Variables opcionales: E2E_SITE, E2E_CONSOLE, E2E_OUT y las credenciales de la Consola (E2E_ADMIN_*, E2E_EDITOR_*).
NO debe apuntarse a un entorno con datos reales: crea cuentas y registros de prueba."""
import json
import os
import random
import re
import struct
import sys
import time
import zlib

from playwright.sync_api import sync_playwright

OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados"))
os.makedirs(OUT, exist_ok=True)
SITE = os.environ.get("E2E_SITE", "http://localhost:5174")
CON = os.environ.get("E2E_CONSOLE", "http://localhost:5173")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@wellq.co.uk")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "Admin123!")
EDITOR_EMAIL = os.environ.get("E2E_EDITOR_EMAIL", "editora@wellq.co.uk")
EDITOR_PASSWORD = os.environ.get("E2E_EDITOR_PASSWORD", "Editora123!")
VIEW = {"width": 1440, "height": 900}
RUN = str(int(time.time()))[-6:]
PW = "Prueba12345!"
EMAIL_FAM, EMAIL_FAM2, EMAIL_CG = f"qa.familia.{RUN}@prueba.cl", f"qa.familia2.{RUN}@prueba.cl", f"qa.cuidador.{RUN}@prueba.cl"
RESULTS = []


def png(path, w=400, h=400, rgb=(90, 120, 200), noise=False):
    Z = bytes([0])
    if noise:
        rows = [Z + os.urandom(w * 3) for _ in range(h)]
    else:
        rows = [Z + b''.join(bytes(((rgb[0] + x // 4) % 256, (rgb[1] + y // 4) % 256, rgb[2])) for x in range(w)) for y in range(h)]

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b''.join(rows)
    sig = bytes.fromhex('89504e470d0a1a0a')
    open(path, 'wb').write(sig + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 1)) + chunk(b'IEND', b''))


FILES = os.path.join(OUT, "files")
os.makedirs(FILES, exist_ok=True)
PHOTO, DOC, BAD, BIG = (os.path.join(FILES, n) for n in ("foto.png", "documento.png", "malo.txt", "grande.png"))
png(PHOTO, rgb=(200, 120, 90))
png(DOC, 300, 200, rgb=(60, 140, 120))
open(BAD, "w").write("esto no es una imagen")
if not os.path.exists(BIG):
    png(BIG, 1700, 1000, noise=True)  # > 4 MB sin comprimir bien


class Ctx:
    def __init__(self, b, name):
        self.name = name
        self.ctx = b.new_context(viewport=VIEW, color_scheme="light")
        self.pg = self.ctx.new_page()
        self.errors = []
        self.pg.on("pageerror", lambda e: self.errors.append(f"JS: {e}"))
        self.pg.on("console", lambda m: self.errors.append(f"console.{m.type}: {m.text[:160]}") if m.type == "error" else None)
        self.pg.on("response", lambda r: self.errors.append(f"HTTP {r.status} {r.request.method} {r.url.split('?')[0][-70:]}") if r.status >= 400 else None)

    def take_errors(self):
        e, self.errors = self.errors, []
        return e


def step(c, name, fn, expect_http=()):
    c.take_errors()
    status, note = "OK", ""
    try:
        note = fn() or ""
    except Exception as e:  # noqa: BLE001
        status, note = "FALLA", str(e).splitlines()[0][:200]
        try:
            c.pg.screenshot(path=os.path.join(OUT, f"fallo_{len(RESULTS)+1:02d}.png"))
        except Exception:  # noqa: BLE001
            pass
    errs = [e for e in c.take_errors() if not any(x in e for x in expect_http)]
    if errs and status == "OK":
        status = "AVISO"
        note = (note + " | " if note else "") + "; ".join(errs[:3])
    elif errs:
        note += " | " + "; ".join(errs[:2])
    RESULTS.append((c.name, name, status, note))
    print(f"[{status}] {c.name}: {name} {('- ' + note) if note else ''}")
    json.dump(RESULTS, open(os.path.join(OUT, "resultados.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def goto(c, url, wait=900):
    c.pg.goto(url)
    c.pg.wait_for_timeout(wait)


def shot(c, name):
    c.pg.screenshot(path=os.path.join(OUT, name))


def register(c, kind, name, email):
    goto(c, SITE + "/registro")
    c.pg.get_by_role("button", name=re.compile("Necesito cuidado" if kind == "family" else "Quiero cuidar")).click()
    c.pg.fill("#fullName", name)
    c.pg.fill("#email", email)
    c.pg.fill("#password", PW)
    c.pg.click("button[type=submit]")
    c.pg.wait_for_url(re.compile(r".*/(familia|cuidadora)$"), timeout=20000)
    c.pg.wait_for_timeout(1000)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        fam, cg, adm, fam2 = Ctx(b, "Familia"), Ctx(b, "Cuidadora"), Ctx(b, "Consola"), Ctx(b, "Familia 2")

        # ---------------- Familia: registro y errores de acceso ----------------
        step(fam, "Registro de familia con cuenta nueva", lambda: register(fam, "family", "Marta Quiroga QA", EMAIL_FAM))
        step(fam, "La familia entra a su inicio con su nombre en la barra", lambda: (
            fam.pg.get_by_text("Marta Quiroga").first.wait_for(timeout=4000), fam.pg.wait_for_selector("text=Mis familiares")) and None)

        def dup():
            c = Ctx(b, "tmp")
            goto(c, SITE + "/registro")
            c.pg.get_by_role("button", name=re.compile("Necesito cuidado")).click()
            c.pg.fill("#fullName", "Otra Persona"); c.pg.fill("#email", EMAIL_FAM); c.pg.fill("#password", PW)
            c.pg.click("button[type=submit]")
            c.pg.wait_for_selector(".error-banner", timeout=6000)
            msg = c.pg.inner_text(".error-banner")
            c.ctx.close()
            return "mensaje: " + msg[:80]
        step(fam, "Correo repetido muestra un error claro", dup, expect_http=("HTTP 409", "HTTP 422", "console.error: Failed to load resource"))

        def badlogin():
            c = Ctx(b, "tmp")
            goto(c, SITE + "/login")
            c.pg.fill("input[type=email]", EMAIL_FAM); c.pg.fill("input[type=password]", "incorrecta123")
            c.pg.click("button[type=submit]")
            c.pg.wait_for_selector(".error-banner", timeout=6000)
            msg = c.pg.inner_text(".error-banner")
            c.ctx.close()
            assert "incorrect" in msg.lower(), msg
            return msg[:80]
        step(fam, "Contraseña incorrecta muestra un error", badlogin, expect_http=("HTTP 401", "console.error: Failed to load resource"))

        def protected():
            c = Ctx(b, "tmp")
            goto(c, SITE + "/familia")
            ok = "/login" in c.pg.url
            c.ctx.close()
            assert ok, "no redirige al login"
        step(fam, "Una ruta protegida sin sesión redirige al login", protected, expect_http=("HTTP 401", "console.error: Failed to load resource"))

        # ---------------- Familia: crear familiar con foto ----------------
        def create_patient():
            goto(fam, SITE + "/familia")
            fam.pg.get_by_text("Crear perfil de un adulto mayor").click()
            fam.pg.wait_for_selector(".modal")
            fam.pg.set_input_files(".modal input[type=file]", PHOTO)
            fam.pg.fill(".modal input >> nth=1", "Rosa Quiroga QA")
            fam.pg.fill(".modal input[type=date]", "1946-05-12")
            fam.pg.fill(".modal input[placeholder='Ej: Penicilina']", "Penicilina")
            fam.pg.keyboard.press("Enter")
            fam.pg.fill(".modal textarea", "Le gusta tejer.")
            fam.pg.click(".modal button.primary")
            fam.pg.wait_for_selector("text=Rosa Quiroga QA", timeout=10000)
            shot(fam, "01_familiar_creado.png")
        step(fam, "Crear un familiar con foto y alergia", create_patient)

        def patient_page():
            fam.pg.locator("a[href^='/familia/']").first.click()
            fam.pg.wait_for_selector("text=Sin cuidadora asignada", timeout=6000)
            shot(fam, "02_ficha_familiar.png")
        step(fam, "La ficha del familiar muestra «Sin cuidadora asignada»", patient_page)

        # ---------------- Cuidadora: registro, perfil, foto y documentos ----------------
        step(cg, "Registro de cuidadora con cuenta nueva", lambda: register(cg, "caregiver", "Pedro Salinas QA", EMAIL_CG))

        def profile():
            cg.pg.wait_for_selector("text=Título profesional", timeout=6000)
            cg.pg.fill("input[placeholder^='Cuidadora certificada']", "Cuidador con 6 años de experiencia")
            cg.pg.fill("textarea", "Acompaño a adultos mayores con paciencia y respeto.")
            cg.pg.fill("input[type=number]", "6")
            for label, text in (("Especialidades", "Alzheimer"), ("Idiomas", "Español"), ("Zonas de cobertura", "Providencia")):
                inp = cg.pg.locator(f"xpath=//label[text()='{label}']/following::input[1]")
                inp.click(); inp.fill(text)
                cg.pg.wait_for_timeout(300)
                cg.pg.locator(".tag-picker-opt").first.click()
            shot(cg, "03_perfil_cuidador_formulario.png")
            cg.pg.locator(".toggle-row .switch").click()
            cg.pg.get_by_role("button", name="Guardar cambios").click()
            cg.pg.wait_for_timeout(2500)
            assert "Perfil guardado" in cg.pg.inner_text("body") or "Editar perfil" in cg.pg.inner_text("body"), "no confirma el guardado"
        step(cg, "Completar y guardar el perfil profesional", profile)

        def photo():
            goto(cg, SITE + "/cuidadora")
            if cg.pg.locator("#avatarInput").count() == 0:
                cg.pg.get_by_role("button", name=re.compile("Editar perfil")).click()
                cg.pg.wait_for_selector("#avatarInput", state="attached")
            cg.pg.set_input_files("#avatarInput", PHOTO)
            cg.pg.wait_for_timeout(2500)
            assert cg.pg.locator(".avatar-img").count() > 0, "la foto no aparece"
            shot(cg, "04_cuidador_con_foto.png")
        step(cg, "Subir la foto de perfil (cuidador)", photo)

        def docs_bad():
            goto(cg, SITE + "/cuidadora")
            cg.pg.wait_for_selector("text=Mis documentos", timeout=6000)
            inp = cg.pg.locator(".doc-card input[type=file]").first
            inp.set_input_files(BAD, timeout=8000)
            cg.pg.wait_for_timeout(800)
            body = cg.pg.inner_text(".doc-card-main") if cg.pg.locator(".doc-card-main").count() else ""
            assert re.search(r"PDF|JPG|PNG", body), "no avisa del formato: " + body[:60]
        step(cg, "Un documento con formato inválido se rechaza con aviso", docs_bad, expect_http=("HTTP 422",))

        def docs_big():
            inp = cg.pg.locator(".doc-card input[type=file]").first
            inp.set_input_files(BIG)
            cg.pg.wait_for_timeout(1500)
            body = cg.pg.inner_text(".doc-card-main") if cg.pg.locator(".doc-card-main").count() else ""
            assert re.search(r"4 ?MB|supera|grande", body), "no avisa del tamaño: " + body[:60]
        step(cg, "Un documento de más de 4 MB se rechaza con aviso", docs_big, expect_http=("HTTP 422",))

        def docs_ok():
            for i in range(3):
                inp = cg.pg.locator(".doc-card input[type=file]").nth(i)
                inp.set_input_files(DOC)
                cg.pg.wait_for_timeout(2200)
            goto(cg, SITE + "/cuidadora")
            cg.pg.wait_for_function("document.body.innerText.split('En revisión').length - 1 >= 3", timeout=12000)
            shot(cg, "05_documentos_en_revision.png")
        step(cg, "Subir los 3 documentos (quedan «En revisión»)", docs_ok)

        def hidden_to_family():
            goto(fam, SITE + "/marketplace")
            fam.pg.wait_for_timeout(1000)
            assert "Pedro Salinas" not in fam.pg.inner_text("body"), "se ve sin estar aprobado"
        step(fam, "La cuidadora NO aparece en la búsqueda mientras no esté aprobada", hidden_to_family)

        # ---------------- Consola ----------------
        def con_login():
            goto(adm, CON + "/login")
            adm.pg.fill("input[type=email]", ADMIN_EMAIL); adm.pg.fill("input[type=password]", ADMIN_PASSWORD)
            adm.pg.click("button[type=submit]")
            adm.pg.wait_for_url(re.compile(r".*/(marketplace|fidelizacion)$"), timeout=15000)
            adm.pg.wait_for_timeout(1500)
            adm.landing = adm.pg.url
            goto(adm, CON + "/marketplace", 1800)
        step(adm, "Ingreso del administrador a la Consola", con_login)

        def con_list():
            adm.pg.reload(); adm.pg.wait_for_timeout(1800)
            row = adm.pg.get_by_text("Pedro Salinas QA")
            assert row.count() > 0, "la cuidadora nueva no llegó a la Consola"
            shot(adm, "06_consola_pendiente.png")
        step(adm, "La cuidadora nueva llega a la Consola como pendiente", con_list)

        def con_approve():
            adm.pg.get_by_text("Pedro Salinas QA").first.click()
            adm.pg.wait_for_selector(".drawer", timeout=6000)
            for _ in range(3):
                btn = adm.pg.locator(".drawer button:has-text('Aprobar')").filter(has_not_text="perfil").first
                btn.click()
                adm.pg.wait_for_timeout(1500)
            shot(adm, "07_consola_documentos_aprobados.png")
            adm.pg.get_by_role("button", name="Aprobar perfil").click()
            adm.pg.wait_for_timeout(2500)
            body = adm.pg.inner_text(".drawer")
            assert re.search(r"Aprobada", body), "no quedó aprobada"
            adm.pg.locator(".drawer-close").click()
        step(adm, "Aprobar los 3 documentos y el perfil", con_approve)

        # ---------------- Familia contrata ----------------
        def family_sees():
            goto(fam, SITE + "/marketplace", 1500)
            body = fam.pg.inner_text("body")
            assert "Pedro Salinas" in body, "no aparece tras la aprobación"
            assert fam.pg.locator(".cg-card img.avatar-img").count() > 0, "las tarjetas no muestran fotos"
            shot(fam, "08_busqueda_con_nuevo.png")
        step(fam, "Tras la aprobación aparece en la búsqueda, con su foto", family_sees)

        def hire_request():
            fam.pg.get_by_text("Pedro Salinas").first.click()
            fam.pg.wait_for_selector("text=Solicitar contratación", timeout=6000)
            fam.pg.get_by_role("button", name="Solicitar contratación").click()
            fam.pg.wait_for_selector(".modal")
            fam.pg.fill(".modal textarea", "Necesitamos apoyo por las mañanas.")
            fam.pg.click(".modal button.primary")
            fam.pg.wait_for_url(re.compile(r".*/mensajes.*"), timeout=10000)
            fam.pg.wait_for_timeout(1500)
            shot(fam, "09_solicitud_chat.png")
        step(fam, "Enviar una solicitud de contratación (abre el chat)", hire_request)

        def cg_accept():
            goto(cg, SITE + "/solicitudes", 1500)
            cg.pg.wait_for_selector("text=Aceptar solicitud", timeout=8000)
            shot(cg, "10_solicitud_recibida.png")
            cg.pg.get_by_role("button", name="Aceptar solicitud").click()
            cg.pg.wait_for_timeout(2500)
            body = cg.pg.inner_text("body")
            assert re.search(r"Aceptaste|Actualmente trabajando", body), "no confirma"
        step(cg, "La cuidadora acepta la solicitud", cg_accept)

        def chat_both():
            goto(fam, SITE + "/mensajes", 1200)
            fam.pg.locator(".chat-item").first.click(); fam.pg.wait_for_timeout(800)
            fam.pg.fill("input[placeholder^='Escribe']", "Hola Pedro, ¿cuándo podemos comenzar?")
            fam.pg.get_by_role("button", name="Enviar").click(); fam.pg.wait_for_timeout(1200)
            goto(cg, SITE + "/mensajes", 1200)
            cg.pg.locator(".chat-item").first.click(); cg.pg.wait_for_timeout(1000)
            assert "cuándo podemos comenzar" in cg.pg.inner_text("body"), "el mensaje no llegó"
            cg.pg.fill("input[placeholder^='Escribe']", "¡Hola! Puedo comenzar el lunes.")
            cg.pg.get_by_role("button", name="Enviar").click(); cg.pg.wait_for_timeout(1000)
            shot(cg, "11_chat_cuidador.png")
        step(cg, "Chat: ida y vuelta entre familia y cuidador", chat_both)

        def working_badge():
            goto(fam, SITE + "/marketplace", 1500)
            card = fam.pg.locator(".cg-card.working").filter(has_text="Pedro")
            assert card.count() == 1, "no se marca «Trabajando»"
            shot(fam, "12_trabajando.png")
        step(fam, "La cuidadora queda marcada como «Trabajando»", working_badge)

        def fam2_blocked():
            register(fam2, "family", "Lucía Torres QA", EMAIL_FAM2)
            goto(fam2, SITE + "/marketplace", 1500)
            fam2.pg.get_by_text("Pedro Salinas").first.click()
            fam2.pg.wait_for_selector("text=En servicio", timeout=6000)
            btn = fam2.pg.get_by_role("button", name="Solicitar contratación")
            assert btn.count() == 0, "otra familia aún puede solicitarla"
        step(fam2, "Otra familia NO puede solicitar a una cuidadora que ya trabaja", fam2_blocked)

        def review_flow():
            goto(fam, SITE + "/marketplace", 1200)
            fam.pg.get_by_text("Pedro Salinas").first.click()
            fam.pg.wait_for_selector("text=Finalizar trabajo", timeout=6000)
            fam.pg.once("dialog", lambda d: d.accept())
            fam.pg.get_by_role("button", name=re.compile("Finalizar trabajo")).click()
            fam.pg.wait_for_timeout(2500)
            fam.pg.get_by_role("button", name=re.compile("Dejar reseña")).click()
            fam.pg.wait_for_selector(".modal")
            fam.pg.locator(".modal button:has-text('5'), .modal button:has-text('★')").last.click()
            fam.pg.fill(".modal textarea", "Excelente trato con mi mamá.")
            fam.pg.click(".modal button.primary")
            fam.pg.wait_for_timeout(2500)
            shot(fam, "13_resena_enviada.png")
        step(fam, "Finalizar el trabajo y dejar una reseña", review_flow)

        def cg_reviews():
            goto(cg, SITE + "/cuidadora", 1500)
            assert "Excelente trato" in cg.pg.inner_text("body"), "la cuidadora no ve su reseña"
            shot(cg, "14_cuidador_resenas.png")
        step(cg, "La cuidadora ve la reseña en su perfil", cg_reviews)

        def con_points():
            goto(adm, CON + "/fidelizacion", 2500)
            body = adm.pg.inner_text("body")
            assert "Pedro Salinas" in body, "no aparece en el ranking"
            shot(adm, "15_consola_ranking.png")
        step(adm, "La Consola refleja la reseña y los puntos en el ranking", con_points)

        # ---------------- Consola: menú, fotos y cambios pedidos ----------------
        def con_menu():
            goto(adm, CON + "/marketplace", 1500)
            nav = adm.pg.inner_text(".c-tabs")
            assert "Contenido" not in nav and "Moderación" not in nav, "siguen Contenido o Moderación: " + nav
            assert "NUEVO" not in nav.upper(), "sigue la etiqueta NUEVO"
            for path in ("/contenido", "/moderacion"):
                goto(adm, CON + path, 900)
                assert adm.pg.locator(".c-tabs").count() > 0
            return "menú: " + nav.replace("\n", " | ")
        step(adm, "El menú ya no tiene Contenido, Moderación ni la etiqueta NUEVO", con_menu)

        def con_photos():
            goto(adm, CON + "/marketplace", 1800)
            n = adm.pg.locator("table.data .person-avatar img").count()
            assert n >= 4, f"solo {n} fotos en la tabla de cuidadoras"
            shot(adm, "16_consola_fotos_marketplace.png")
            goto(adm, CON + "/fidelizacion", 2200)
            m = adm.pg.locator("table.data .person-avatar img").count()
            assert m >= 3, f"solo {m} fotos en el ranking"
            shot(adm, "17_consola_fotos_ranking.png")
            return f"{n} fotos en el listado y {m} en el ranking"
        step(adm, "La Consola muestra la foto de cada cuidadora (listado y ranking)", con_photos)

        def con_new_photo():
            goto(adm, CON + "/marketplace", 1800)
            adm.pg.get_by_text("Pedro Salinas QA").first.click()
            adm.pg.wait_for_selector(".drawer .person-avatar img", timeout=6000)
        step(adm, "La foto que subió el cuidador nuevo llegó a la Consola", con_new_photo)

        def home_is_marketplace():
            c = Ctx(b, "tmp")
            goto(c, CON + "/login")
            c.pg.fill("input[type=email]", EDITOR_EMAIL); c.pg.fill("input[type=password]", EDITOR_PASSWORD)
            c.pg.click("button[type=submit]")
            c.pg.wait_for_url(re.compile(r".*/marketplace$"), timeout=15000)
            c.ctx.close()
        step(adm, "Un rol de editor entra directo a Marketplace", home_is_marketplace)

        def quick_photo():
            goto(cg, SITE + "/cuidadora", 1500)
            cg.pg.locator(".quick-avatar input[type=file]").set_input_files(PHOTO)
            cg.pg.wait_for_timeout(2500)
            assert cg.pg.locator(".quick-avatar .avatar-img").count() > 0
        step(cg, "La cuidadora cambia su foto desde la vista del perfil (botón de cámara)", quick_photo)

        def seeded_photos():
            goto(fam, SITE + "/marketplace", 1800)
            n = fam.pg.locator(".cg-card img.avatar-img").count()
            assert n >= 6, f"solo {n} tarjetas con foto"
            shot(fam, "18_busqueda_con_fotos.png")
            return f"{n} tarjetas con foto"
        step(fam, "Las tarjetas de cuidadoras y cuidadores muestran su foto", seeded_photos, expect_http=("HTTP 401", "console.error: Failed to load resource"))

        # ---------------- Navegación general ----------------
        def nav_pages():
            for path in ("/familia", "/marketplace", "/marketplace/productos", "/mensajes"):
                goto(fam, SITE + path, 1200)
                assert fam.pg.locator(".page").count() > 0, f"{path} no carga"
        step(fam, "Todas las pantallas de la familia cargan sin errores", nav_pages)

        def logout():
            fam.pg.get_by_role("button", name="Salir").click()
            fam.pg.wait_for_timeout(1200)
            goto(fam, SITE + "/familia")
            assert "/login" in fam.pg.url, "la sesión no se cerró"
        step(fam, "Cerrar sesión", logout, expect_http=("HTTP 401", "console.error: Failed to load resource"))

        try:
            b.close()
        except Exception:
            pass

    json.dump(RESULTS, open(os.path.join(OUT, "resultados.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in RESULTS if r[2] == "OK")
    print(f"\n== {ok}/{len(RESULTS)} OK; fallas: {sum(1 for r in RESULTS if r[2]=='FALLA')}, avisos: {sum(1 for r in RESULTS if r[2]=='AVISO')}")


if __name__ == "__main__":
    main()
