# -*- coding: utf-8 -*-
"""Genera "Registro_de_cambios_AgeCare.pdf" a partir de cambios.json.

Uso:  python generar_pdf.py
Cada vez que se haga un cambio en el proyecto, se agrega una entrada AL INICIO de cambios.json
(fecha, titulo, resumen, areas con items, pasos_manuales) y se vuelve a correr este script.
Requiere: pip install reportlab
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

HERE = Path(__file__).parent
OUT = HERE / "Registro_de_cambios_AgeCare.pdf"

INDIGO = colors.HexColor("#3649C8")
INK = colors.HexColor("#12164A")
MUTED = colors.HexColor("#5A6072")
GOLD = colors.HexColor("#FFC700")
SOFT = colors.HexColor("#F2F4FF")

title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, leading=28, textColor=INK, spaceAfter=4)
sub = ParagraphStyle("s", fontName="Helvetica", fontSize=10, leading=14, textColor=MUTED, spaceAfter=14)
date_s = ParagraphStyle("d", fontName="Helvetica-Bold", fontSize=9.5, textColor=INDIGO, spaceBefore=16, spaceAfter=2)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14.5, leading=19, textColor=INK, spaceAfter=3)
summary = ParagraphStyle("sm", fontName="Helvetica-Oblique", fontSize=10, leading=14, textColor=MUTED, spaceAfter=6)
area = ParagraphStyle("a", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=INDIGO, spaceBefore=8, spaceAfter=3)
item = ParagraphStyle("i", fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=2.5)
todo_h = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#8A6300"), spaceBefore=8, spaceAfter=2)
todo = ParagraphStyle("td", parent=item, textColor=colors.HexColor("#5A4500"))


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "AgeCare - Registro de cambios - Equipo DACA_10")
    canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def build() -> None:
    entries = json.loads((HERE / "cambios.json").read_text(encoding="utf-8"))
    story = [Paragraph("AgeCare - Registro de cambios", title),
             Paragraph("Historial de todo lo que se ha cambiado en el proyecto (sitio de familias y cuidadoras, "
                       "Consola de administración y APIs). Lo más reciente está primero.", sub)]
    for e in entries:
        block = [Paragraph(esc(e["fecha"]), date_s), Paragraph(esc(e["titulo"]), h1)]
        if e.get("resumen"):
            block.append(Paragraph(esc(e["resumen"]), summary))
        story.append(KeepTogether(block))
        for a in e.get("areas", []):
            story.append(Paragraph(esc(a["nombre"]), area))
            for it in a["items"]:
                story.append(Paragraph(esc(it), item, bulletText="•"))
        if e.get("pasos_manuales"):
            story.append(Paragraph("Pasos manuales pendientes", todo_h))
            for p in e["pasos_manuales"]:
                story.append(Paragraph(esc(p), todo, bulletText="•"))
        story.append(Spacer(1, 6))

    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="AgeCare - Registro de cambios", author="Equipo DACA_10")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF generado:", OUT)


if __name__ == "__main__":
    build()
