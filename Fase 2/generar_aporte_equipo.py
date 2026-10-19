"""Genera `Aporte del equipo.md` a partir del historial de Git (evidencia del aporte de cada integrante).

Uso (desde la raíz del repositorio):  python "Fase 2/generar_aporte_equipo.py"
Se puede volver a ejecutar cuando haya commits nuevos: el archivo se reescribe completo.
"""
import collections
import datetime
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aporte del equipo.md")

AREAS = {
    "frontend": "Consola de Administración (interfaz)",
    "backend": "API de la Consola de Administración",
    "webapp": "Sitio público (interfaz)",
    "backend-general": "API del sitio público",
    "deploy": "Despliegue (Vercel y Supabase)",
    "Fase 1": "Evidencias académicas",
    "Fase 2": "Evidencias académicas",
    "Registro de cambios": "Documentación",
}


def integrante(nombre: str) -> str:
    return "Julio Muñoz" if "julio" in nombre.lower() else "Bryan Piña"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout


def area_de(ruta: str) -> str:
    top = ruta.split("/")[0]
    return AREAS.get(top, "Documentación" if top.lower().endswith(".md") else "Otros")


def main() -> None:
    salida = git("log", "--no-merges", "--name-only", "--format=@@%h|%an|%ad|%s", "--date=short")
    commits = []  # (hash, autor, fecha, asunto, {areas})
    for linea in salida.splitlines():
        if linea.startswith("@@"):
            h, autor, fecha, asunto = linea[2:].split("|", 3)
            commits.append([h, integrante(autor), fecha, asunto, collections.Counter()])
        elif linea.strip() and commits:
            commits[-1][4][area_de(linea.strip())] += 1

    por_autor = collections.defaultdict(list)
    for c in commits:
        por_autor[c[1]].append(c)

    hoy = datetime.date.today().strftime("%d-%m-%Y")
    md = ["# Aporte de cada integrante al repositorio", "",
          f"Generado con `git log` el {hoy} (`python \"Fase 2/generar_aporte_equipo.py\"`). "
          "Cada fila sale del historial público del repositorio; no se edita a mano.", "",
          "## Resumen", "",
          "| Integrante | Commits | Primer commit | Último commit | Áreas donde trabajó (archivos modificados) |",
          "|---|---|---|---|---|"]
    for nombre in ("Bryan Piña", "Julio Muñoz"):
        lista = por_autor.get(nombre, [])
        if not lista:
            continue
        areas = collections.Counter()
        for c in lista:
            areas.update(c[4])
        texto = "; ".join(f"{a} ({n})" for a, n in areas.most_common(6))
        fechas = sorted(c[2] for c in lista)
        md.append(f"| {nombre} | {len(lista)} | {fechas[0]} | {fechas[-1]} | {texto} |")
    md += ["", "El conteo de archivos incluye un mismo archivo cada vez que se modifica; "
               "no mide el esfuerzo, solo muestra dónde trabajó cada persona.", ""]

    for nombre in ("Bryan Piña", "Julio Muñoz"):
        lista = por_autor.get(nombre, [])
        if not lista:
            continue
        md += [f"## Commits de {nombre}", "", "| Fecha | Commit | Descripción |", "|---|---|---|"]
        for h, _, fecha, asunto, _ in sorted(lista, key=lambda c: c[2]):
            md.append(f"| {fecha} | `{h}` | {asunto} |")
        md.append("")

    md += ["## Dónde ver el trabajo de cada uno", "",
           "- Historial completo: <https://github.com/Bemol69/BryanPi-a_JulioMunoz_ProyectoDeTitulo_AgecARE/commits/main>",
           "- Por integrante: en GitHub, *Insights → Contributors*.",
           "- Cambios del sistema con fecha: carpeta `Registro de cambios/`.", ""]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md))
    print("ok", OUT)


if __name__ == "__main__":
    main()
