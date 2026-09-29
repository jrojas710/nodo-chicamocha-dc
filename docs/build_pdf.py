#!/usr/bin/env python3
"""
build_pdf.py — genera el expediente del cliente (PDF) del Parcial 1.

  python docs/build_pdf.py            -> docs/Parcial1_NodoChicamochaDC_JuanRojas.pdf

Inserta automáticamente:
  * capturas reales colocadas en evidencias/ (nombres en evidencias/README.md);
  * estadísticas y gráficos de datos_4dias/resultados/ (tools/analisis_4dias.py).
Lo que falte aparece como recuadro PENDIENTE, para no presentar datos inventados.
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from catalogo import (ARTIFACT_VERSIONS, DEVICES, PROJECT, RULES, TEMPLATES,  # noqa: E402
                      VARS, VERSIONS)

ASSETS, EVID, RES = HERE / "assets", ROOT / "evidencias", ROOT / "datos_4dias" / "resultados"
OUT = HERE / "Parcial1_NodoChicamochaDC_JuanRojas.pdf"

FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", FD + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

NAVY, TEAL, AMBER, RED = (colors.HexColor(c) for c in ("#0F2A44", "#1C8C8C", "#E0A100", "#B3261E"))
LIGHT, GRID, MUTED = colors.HexColor("#EEF3F7"), colors.HexColor("#C9D3DD"), colors.HexColor("#5B6673")

S = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.4, leading=13.4, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="DV", fontSize=7.6, leading=9.6),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=7.1, leading=8.9),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=7.1, leading=8.9, textColor=colors.white),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19, textColor=NAVY,
                         spaceBefore=4, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=11.2, leading=14.5, textColor=TEAL,
                         spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "cap": ParagraphStyle("cap", fontName="DVI", fontSize=7.8, leading=10, textColor=MUTED,
                          alignment=TA_CENTER, spaceBefore=2, spaceAfter=8),
    "code": ParagraphStyle("code", fontName="DVM", fontSize=7.3, leading=9.4, backColor=LIGHT,
                           borderPadding=5, spaceBefore=3, spaceAfter=8),
    "note": ParagraphStyle("note", fontName="DV", fontSize=8.4, leading=11.4, backColor=colors.HexColor("#FFF6DC"),
                           borderColor=AMBER, borderWidth=0.8, borderPadding=6, spaceBefore=4, spaceAfter=10),
}
W = A4[0] - 4.0 * cm   # ancho útil


# --------------------------------------------------------------------------- doc
class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                         topMargin=2.4 * cm, bottomMargin=2.0 * cm,
                         title="Parcial 1 · Nodo Chicamocha DC · IoT Central",
                         author=PROJECT["author"], subject="Expediente del cliente — escenario 5.2 Centro de datos")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate("cover", [frame], onPage=self._cover),
                               PageTemplate("body", [frame], onPage=self._page)])
        self._h = [0, 0]

    def _cover(self, c, d):
        c.saveState()
        c.setFillColor(NAVY); c.rect(0, A4[1] - 7.2 * cm, A4[0], 7.2 * cm, stroke=0, fill=1)
        c.setFillColor(TEAL); c.rect(0, A4[1] - 7.45 * cm, A4[0], 0.25 * cm, stroke=0, fill=1)
        c.setFillColor(NAVY); c.rect(0, 0, A4[0], 1.2 * cm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("DV", 7.5)
        c.drawString(2 * cm, 0.5 * cm, f"{PROJECT['university']} · {PROJECT['course']} · {PROJECT['exam']}")
        c.restoreState()

    def _page(self, c, d):
        c.saveState()
        c.drawImage(str(ASSETS / "logo.png"), 2 * cm, A4[1] - 1.85 * cm, 0.95 * cm, 0.95 * cm, mask="auto")
        c.setFont("DVB", 8.4); c.setFillColor(NAVY)
        c.drawString(3.15 * cm, A4[1] - 1.3 * cm, PROJECT["name"])
        c.setFont("DV", 7.4); c.setFillColor(MUTED)
        c.drawString(3.15 * cm, A4[1] - 1.66 * cm, "Expediente del cliente · Parcial 1 IoT Central")
        c.drawRightString(A4[0] - 2 * cm, A4[1] - 1.3 * cm, PROJECT["university"])
        c.drawRightString(A4[0] - 2 * cm, A4[1] - 1.66 * cm, PROJECT["exam"])
        c.setStrokeColor(TEAL); c.setLineWidth(1.2)
        c.line(2 * cm, A4[1] - 2.0 * cm, A4[0] - 2 * cm, A4[1] - 2.0 * cm)
        c.setStrokeColor(GRID); c.setLineWidth(.5); c.line(2 * cm, 1.45 * cm, A4[0] - 2 * cm, 1.45 * cm)
        c.drawString(2 * cm, 1.0 * cm, f"{PROJECT['author']} · Documento v{PROJECT['doc_version']}")
        c.drawRightString(A4[0] - 2 * cm, 1.0 * cm, f"Página {d.page}")
        c.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            lvl = 0 if f.style.name == "h1" else 1
            txt = f.getPlainText()
            key = f"k{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=lvl, closed=lvl > 0)
            self.notify("TOCEntry", (lvl, txt, self.page, key))


story: list = []
sec = [0, 0]


def h1(t):
    sec[0] += 1; sec[1] = 0
    story.append(Paragraph(f"{sec[0]}. {t}", S["h1"]))


def h2(t):
    sec[1] += 1
    story.append(Paragraph(f"{sec[0]}.{sec[1]} {t}", S["h2"]))


def p(t, st="body"):
    story.append(Paragraph(t, S[st]))


def bullets(items, st="body"):
    for it in items:
        story.append(Paragraph(f"•&nbsp;&nbsp;{it}", ParagraphStyle("b", parent=S[st], leftIndent=12,
                                                                        firstLineIndent=-9, spaceAfter=2.5)))
    story.append(Spacer(1, 4))


def table(head, rows, widths, zebra=True, font=None):
    cs = S["cell"] if font is None else font
    data = [[Paragraph(str(h), S["cellb"]) for h in head]]
    data += [[Paragraph("" if v is None else str(v), cs) for v in r] for r in rows]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("TOPPADDING", (0, 0), (-1, -1), 3),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4),
          ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if zebra:
        st += [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(st))
    story.append(t); story.append(Spacer(1, 8))


def figure(path, caption, width=1.0, max_h=None):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(path)).getSize()
    w = W * width
    h = w * ih / iw
    if max_h and h > max_h:
        h = max_h; w = h * iw / ih
    story.append(KeepTogether([Image(str(path), w, h), Paragraph(caption, S["cap"])]))


def evidence(name, caption, what, width=0.95, max_h=11 * cm):
    for ext in (".png", ".jpg", ".jpeg"):
        f = EVID / (Path(name).stem + ext)
        if f.is_file():
            figure(f, caption + " (captura de IoT Central)", width, max_h)
            return
    box = Table([[Paragraph(f"<b>PENDIENTE · captura real</b> — guarde la imagen como "
                            f"<font face='DVM'>evidencias/{name}</font> y ejecute "
                            f"<font face='DVM'>python docs/build_pdf.py</font>.<br/>"
                            f"<b>Debe mostrar:</b> {what}", S["small"])]], colWidths=[W * 0.95])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, AMBER), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEF")),
                             ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    story.append(KeepTogether([box, Paragraph(caption, S["cap"])]))


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# =========================================================================== PORTADA
story.append(Spacer(1, 1.1 * cm))
cover_title = ParagraphStyle("ct", fontName="DVB", fontSize=25, leading=30, textColor=colors.white)
cover_sub = ParagraphStyle("cs", fontName="DV", fontSize=11.5, leading=15, textColor=colors.HexColor("#CFE6E6"))
story.append(Paragraph("NODO CHICAMOCHA DC", cover_title))
story.append(Paragraph("Monitoreo IoT de un centro de datos urbano sobre Azure IoT Central", cover_sub))
story.append(Spacer(1, 2.4 * cm))
story.append(Table([[Image(str(ASSETS / "logo.png"), 6.2 * cm, 6.2 * cm)]], colWidths=[W],
                   style=[("ALIGN", (0, 0), (-1, -1), "CENTER")]))
story.append(Spacer(1, 0.7 * cm))
ctr = ParagraphStyle("ctr", fontName="DVB", fontSize=14, leading=18, alignment=TA_CENTER, textColor=NAVY)
story.append(Paragraph("PARCIAL 1 · Escenario IoT Central con flota heterogénea de 10 dispositivos", ctr))
story.append(Paragraph("Escenario 5.2 — Centro de datos · Expediente del cliente",
                       ParagraphStyle("c2", parent=S["body"], alignment=TA_CENTER, textColor=TEAL, fontSize=11)))
story.append(Spacer(1, 0.8 * cm))
meta = [["Cliente (caso)", PROJECT["company"]], ["Autor", PROJECT["author"]],
        ["Asignatura", PROJECT["course"]], ["Institución", PROJECT["university"]],
        ["Periodo", PROJECT["exam"]], ["Sitio", PROJECT["site"]],
        ["Versión del documento", f"{PROJECT['doc_version']} · {date(2026, 9, 28).isoformat()}"]]
mt = Table([[Paragraph(f"<b>{a}</b>", S["body"]), Paragraph(b, S["body"])] for a, b in meta],
           colWidths=[4.5 * cm, W - 4.5 * cm])
mt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), .4, GRID), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
story.append(mt)
story.append(NextPageTemplate("body")); story.append(PageBreak())

# =========================================================================== VERSIONES + ÍNDICE
story.append(Paragraph("Historial de versiones", S["h1"]))
table(["Versión", "Fecha", "Autor", "Cambio"], VERSIONS, [.09, .13, .2, .58])
story.append(Paragraph("Versiones de artefactos (Device Template y scripts)", S["h2"]))
table(["Artefacto", "Versión", "Detalle"], ARTIFACT_VERSIONS, [.42, .12, .46])
p("Regla de versionado: cambiar un campo de una plantilla publicada exige nueva versión del modelo "
  "(<font face='DVM'>;1 → ;2</font>) y migrar los dispositivos en IoT Central; los scripts siguen SemVer y "
  "reportan su versión como propiedad <font face='DVM'>firmwareVersion</font>, visible en la vista del dispositivo.")
story.append(Spacer(1, 6))
story.append(Paragraph("Contenido", S["h1"]))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t0", fontName="DVB", fontSize=9.2, leading=13, leftIndent=0),
                   ParagraphStyle("t1", fontName="DV", fontSize=8.4, leading=11, leftIndent=14, textColor=MUTED)]
story.append(toc)
story.append(PageBreak())

# =========================================================================== 1 RESUMEN
h1("Resumen ejecutivo")
p("<b>Chicamocha Data Center S.A.S.</b> (cliente del caso) opera una sala blanca urbana en Bucaramanga con una fila de "
  "tres racks. Solicita un <b>demo funcional</b> de monitoreo en Azure IoT Central que un operador no programador "
  "pueda leer desde un cuarto de control: mapa térmico de los tres armarios, alarmas de agua, humo y energía, "
  "estado de contención de pasillo frío, acceso a la sala y las condiciones exteriores que habilitan el free-cooling.")
p("La solución despliega <b>10 dispositivos con 10 orígenes de envío distintos</b> (Python SDK, Wokwi ESP32, "
  "simulador nativo del Digital Twin, Python por WebSockets, feed meteorológico, API pública de calidad de aire, "
  "cliente MQTT explícito, replay CSV por AMQP, puente HTTP/REST y una segunda instancia Wokwi), cuatro protocolos "
  "de transporte (MQTT, MQTT-WS, AMQP y HTTPS) y <b>siete cadencias</b> distintas (15 s a 15 min, más envío por evento). "
  "Ocho plantillas DTDL modelan el Digital Twin; catorce Rules separadas por categoría generan las alertas.")
bullets([
    "<b>Indispensables del escenario cubiertos:</b> temperatura y humedad en los racks A, B y C (DEV-01/02/03); "
    "control room con mapa térmico y alarmas de agua (DEV-07), humo (DEV-08) y energía (DEV-09).",
    "<b>Orígenes obligatorios presentes:</b> Digital Twin/simulador (DEV-03), Wokwi (DEV-02), Python (DEV-01), "
    "API pública (DEV-06), feed meteorológico equivalente a Atlas Weather (DEV-05).",
    "<b>Nodos en vivo de la sustentación:</b> DEV-01 (Python en el portátil 1) y DEV-02 (Wokwi en el portátil 2). "
    "Ambos implementan el comando <font face='DVM'>simulateOutage</font> para reproducir la desconexión y reconexión.",
    "<b>Evidencia real:</b> las secciones 8 a 10 reciben las capturas de IoT Central y las estadísticas "
    "del export de los 4 días. Si aparece un recuadro <b>PENDIENTE</b>, esa evidencia aún no se ha cargado.",
])

# =========================================================================== 2 ESCENARIO
h1("Escenario y criterios de diseño")
h2("Por qué el escenario 5.2")
p("El centro de datos tiene criterios de aceptación cuantitativos publicados (ASHRAE TC 9.9 para la envolvente "
  "térmica de equipos de TI clase A1 y TIA-942 como marco académico de disponibilidad). Esto permite que cada "
  "umbral de Rule se justifique con una referencia y no con una cifra arbitraria. Además, es un sitio urbano con "
  "fibra, lo que simplifica la capa de telecomunicaciones y concentra el esfuerzo en la heterogeneidad de orígenes.")
h2("Requisitos del cliente → decisión de diseño")
table(["Requisito", "Decisión"], [
    ["Tres racks con T y HR (indispensable)", "Plantilla única RackThermal para A, B y C; cada rack con un origen distinto (Python, Wokwi, simulador) para comparar comportamiento real vs. simulado."],
    ["Mapa térmico de los tres armarios", "Tile de mapa de calor / KPI con tempIntake y tempExhaust de A/B/C en el dashboard."],
    ["Alarmas de agua, humo y energía", "Rules críticas R06, R08 y R10 con acción de correo y webhook; bloque de alertas en el control room."],
    ["Contención de pasillos", "Presión diferencial (Pa) frío-caliente; una caída bajo 2 Pa indica puerta de contención abierta o paneles ciegos faltantes."],
    ["Free-cooling", "Clima exterior real de Bucaramanga (feed meteorológico) y calidad del aire de admisión (API pública) para decidir apertura de dampers."],
    ["Seguridad física", "Puerta con contacto magnético y lector de credencial; Rules de puerta retenida e intentos rechazados."],
], [.34, .66])
h2("Envolvente térmica de referencia (ASHRAE A1)")
p("Rango recomendado de temperatura de entrada 18–27 °C; permisible A1 15–32 °C; punto de rocío recomendado "
  "−9 a 15 °C con humedad relativa ≤ 60 %. De aquí salen R01 (&gt; 27 °C aviso), R02 (&gt; 32 °C crítico), "
  "R03 (HR &gt; 60 % o &lt; 20 %) y R05 (punto de rocío &gt; 15 °C).")

# =========================================================================== 3 ARQUITECTURA
h1("Arquitectura de referencia")
p("La figura 1 muestra la flota completa en cuatro capas. El color del borde de cada dispositivo indica su "
  "protocolo de transporte hacia Azure. Todos los enlaces viajan cifrados con TLS 1.2 y se autentican con tokens "
  "SAS derivados de la clave del grupo de conexión de IoT Central; ninguna credencial queda en el código fuente.")
figure(ASSETS / "arquitectura.png", "Figura 1. Arquitectura de referencia de la flota (dispositivo, red, plataforma, operación).",
       width=0.93, max_h=21.5 * cm)
h2("Capa de telecomunicaciones")
table(["Protocolo", "Puerto", "Dispositivos", "Autenticación / sesión", "Justificación"], [
    ["MQTT 3.1.1 / TLS 1.2", "8883/TCP", "01, 02, 05, 06, 07, 10", "SAS en password; keep-alive 60–120 s; sesión persistente", "Bidireccional (comandos, twin), bajo overhead; estándar de IoT Hub."],
    ["MQTT sobre WebSockets", "443/TCP", "04", "SAS; túnel wss://", "Redes corporativas que solo permiten 443; valida la ruta alterna."],
    ["AMQP 1.0 / TLS", "5671/TCP", "08", "SAS (CBS); enlace multiplexado", "Protocolo de gateways y backends; tercer transporte de la flota."],
    ["HTTPS REST", "443/TCP", "09", "SAS por petición; sin sesión", "Gateways simples/Modbus que publican por lotes; sin comandos en tiempo real."],
    ["Interno", "—", "03", "Gestionado por IoT Central", "Simulador nativo del Digital Twin."],
], [.17, .09, .15, .27, .32])
table(["Elemento de red", "Especificación", "Riesgo que mitiga"], [
    ["Acceso local", "Ethernet 1 GbE en la sala para VM y gateway; Wi-Fi WPA2-Enterprise 2,4 GHz para ESP32 (en la simulación: SSID Wokwi-GUEST)", "Separación de VLAN de monitoreo respecto a la red de producción"],
    ["Salida a Internet", "Fibra FTTH del ISP urbano + router 4G/LTE de respaldo con conmutación automática", "Caída del ISP: la telemetría sigue saliendo por LTE"],
    ["Firewall", "Solo salida hacia *.azure-devices.net y *.azure-devices-provisioning.net en 8883, 443 y 5671; sin puertos de entrada", "Superficie de ataque mínima: el dispositivo siempre inicia la conexión"],
    ["DNS y NTP", "Resolución de los hosts de Azure; NTP obligatorio porque el token SAS tiene expiración en UTC", "Tokens rechazados por desfase de reloj"],
    ["DPS", "global.azure-devices-provisioning.net con ID scope de la app; payload {modelId}", "Asignación automática de plantilla y del hub interno"],
], [.18, .5, .32])

# =========================================================================== 4 DIGITAL TWIN
h1("Digital Twin: plantillas de dispositivo")
p("Cada plantilla es una interfaz DTDL v2 generada desde <font face='DVM'>docs/catalogo.py</font> por "
  "<font face='DVM'>templates/gen_dtdl.py</font> e importada en IoT Central (Device templates → IoT device → "
  "Import a model). Todas incluyen las propiedades comunes <font face='DVM'>firmwareVersion</font>, "
  "<font face='DVM'>sourceOrigin</font> y <font face='DVM'>lastBoot</font> para que el operador vea qué origen y "
  "qué versión de código alimenta cada gemelo. Las telemetrías con tipo semántico (Temperature, RelativeHumidity, "
  "Pressure, Power, Energy…) llevan su unidad en el modelo.")
rows = []
for k, t in TEMPLATES.items():
    tel = [i[0] for i in t["items"] if i[1] == "T"]
    wr = [i[0] for i in t["items"] if i[1] == "W"]
    cm_ = [i[0] for i in t["items"] if i[1] == "C"]
    devs = ", ".join(d["n"] for d in DEVICES if d["template"] == k)
    rows.append([f"<b>{t['display']}</b><br/><font face='DVM' size='6.3'>{t['model']}</font>",
                 ", ".join(tel), ", ".join(wr) or "—", ", ".join(cm_) or "—", devs])
table(["Plantilla / modelId", "Telemetría", "Escribibles", "Comandos", "DEV"], rows, [.25, .36, .14, .17, .08])
h2("Vistas por plantilla")
bullets(["<b>Overview (operador):</b> último valor de cada variable, gráfico de 24 h y estado de conexión.",
         "<b>Properties:</b> formulario con las propiedades escribibles (umbral local, intervalo de muestreo) y las de solo lectura (versión, origen, marca de tiempo de la fuente).",
         "<b>Commands:</b> generada por la plataforma a partir de los comandos del modelo (setFanBoost, simulateOutage, unlockDoor, resetLeakLatch…).",
         "La identidad visual (logo, colores) se configura en Customization → Appearance de la aplicación."])
evidence("01_plantillas.png", "Evidencia 1. Plantillas publicadas en IoT Central.", "la lista de Device templates con las 8 plantillas en estado Published.")
evidence("17_simulado_props.png", "Evidencia 2. Rack C simulado (Digital Twin) con propiedad editada.",
         "el dispositivo dc-rack-c-sim con telemetría periódica y la propiedad intakeAlarmC modificada desde la vista Properties.")

# =========================================================================== 5 CATÁLOGO
h1("Catálogo único de 10 dispositivos")
p("Una sola tabla, diez filas y diez orígenes distinguibles. La flota no se parte en bloques: cada fila tiene "
  "un código o un feed diferente, y todos los orígenes obligatorios de la sección 3 del enunciado están presentes.")
table(["#", "ID en Central", "Zona", "Origen de envío", "Protocolo", "Intervalo", "Variables", "Datasheet citado"],
      [[d["n"], f"<font face='DVM' size='6.4'>{d['id']}</font>", d["zona"], d["origen"], d["protocolo"],
        d["intervalo"], d["variables"], d["datasheet"]] for d in DEVICES],
      [.04, .15, .11, .14, .14, .09, .18, .15])
h2("Por qué cada origen es distinto y cómo se provisiona")
table(["#", "Qué lo hace distinto", "Provisionamiento", "Dónde corre", "Código"],
      [[d["n"], d["distinto"],
        {"03": "Creado en Central con Simulate = Yes",
         "02": "DPS REST (tools/provision.py) → hub + clave en secrets.h",
         "10": "DPS REST (tools/provision.py) → hub + clave en secrets.h",
         "07": "DPS REST desde el script (payload modelId)",
         "09": "DPS REST desde el script (payload modelId)",
         "08": "DPS por AMQP con SDK de Node.js"}.get(d["n"], "DPS con SDK Python, clave simétrica derivada"),
        d["corre"], f"<font face='DVM' size='6.2'>{d['codigo']}</font>"] for d in DEVICES],
      [.04, .36, .22, .15, .23])
figure(ASSETS / "mapa_zonas.png", "Figura 2. Mapa de zonas: relación dispositivo ↔ lugar físico (también se usa como tile de imagen del dashboard).", 0.9)

# =========================================================================== 6 PARÁMETROS
h1("Tablas de parámetros por variable")
p("Cada variable queda anclada a un sensor o equipo real. La columna <i>Código</i> muestra los valores exactos "
  "usados en los scripts (base, amplitud del perfil diario, límites de recorte y offset de calibración) o, en los "
  "orígenes de API, la ventana de validación que descarta datos físicamente imposibles. Los rangos del fabricante "
  "deben contrastarse con la hoja de datos vigente de cada referencia (anexo C) antes de la entrega final.")
table(["DEV", "Variable", "Unidad", "Rango datasheet", "Rango operativo", "Precisión", "Umbral de Rule", "Código (min/max/offset)"],
      VARS, [.06, .12, .06, .17, .14, .12, .15, .18])
p("<b>Nota sobre DEV-01/02/03:</b> se usa la misma plantilla y los mismos umbrales para los tres racks. La precisión "
  "del DHT22 (Rack B, Wokwi) es menor que la del SHT45 (Rack A); por eso el umbral de aviso se evalúa sobre el "
  "promedio de 5 minutos y no sobre muestras individuales.", "note")

# =========================================================================== 7 RULES
h1("Rules y alertas")
p("Las Rules están separadas por categoría y ningún umbral se comparte entre categorías. Las de variables "
  "analógicas usan agregación temporal de 5 min para evitar alertas por ruido; las binarias (fuga, humo, breaker) "
  "se evalúan sin agregación porque su latencia importa más que su estabilidad.")
table(["ID", "Categoría", "Nombre", "Plantilla", "Condición", "Severidad", "Acción"], RULES,
      [.06, .1, .17, .14, .25, .1, .18])
evidence("04_rules.png", "Evidencia 3. Rules configuradas y habilitadas.", "la lista de Rules R01–R14 habilitadas.")

# =========================================================================== 8 ASINCRONÍA
h1("Asincronía, desconexión y operación en línea")
h2("Asincronía por diseño")
p("La flota usa siete cadencias: 15 s, 30 s, 60 s, 120 s, 5 min, 15 min y la del simulador, más dos dispositivos "
  "que envían solo ante eventos con latido periódico. Esto supera el mínimo de tres intervalos. La figura 3 es el "
  "diseño que queda en el código; la evidencia 4 debe mostrar ese mismo patrón en los datos de IoT Central.")
figure(ASSETS / "cadencias.png", "Figura 3. Diseño de cadencias (ilustrativo, derivado de los intervalos del código; no es una captura).")
intervals = RES / "intervalos.csv"
if intervals.is_file():
    rows = read_csv(intervals)
    table(["Dispositivo", "Día", "Intervalo mediano medido (s)", "Muestras"],
          [[r["dispositivo"], r.get("dia", ""), r["intervalo_mediano_s"], r["muestras"]] for r in rows], [.35, .2, .3, .15])
    p("Intervalos medidos sobre el export real de IoT Central (tools/analisis_4dias.py).", "small")
evidence("10_asincronia.png", "Evidencia 4. Asincronía observada en IoT Central.",
         "un gráfico de Data Explorer con al menos tres dispositivos de intervalos distintos (por ejemplo DEV-01 a 15 s, DEV-04 a 60 s y DEV-09 a 5 min).")
h2("Desconexión controlada y reconexión")
p("Procedimiento reproducible (se ejecuta en la sustentación con DEV-01 o DEV-02):")
bullets(["En IoT Central → dispositivo → Commands → <font face='DVM'>simulateOutage</font> con valor 240.",
         "El dispositivo responde 200, cierra su sesión MQTT y deja de publicar; el log muestra "
         "<font face='DVM'>=== DESCONEXIÓN CONTROLADA 240 s ===</font> y Central lo marca <b>Disconnected</b>.",
         "A los 240 s el código vuelve a abrir la sesión (<font face='DVM'>=== RECONEXIÓN ===</font>), el estado pasa a "
         "<b>Connected</b> y la serie retoma. En el gráfico queda un hueco de ≈ 4 min.",
         "Alternativas equivalentes: Ctrl+C del script (apagado controlado), detener la simulación en Wokwi o "
         "desconectar el Wi-Fi del portátil (fallo de red). El SDK y paho reconectan con backoff exponencial."])
gaps = RES / "huecos.csv"
if gaps.is_file() and read_csv(gaps):
    table(["Dispositivo", "Desde", "Hasta", "Duración (min)"],
          [[r["dispositivo"], r["desde"][:16].replace("T", " "), r["hasta"][:16].replace("T", " "), r["duracion_min"]]
           for r in read_csv(gaps)[:20]], [.3, .27, .27, .16])
    p("Huecos detectados automáticamente en el export (intervalo &gt; 3× el mediano).", "small")
evidence("11_desconexion_hueco.png", "Evidencia 5. Hueco en la serie y reconexión.", "la serie de DEV-01 o DEV-02 con el hueco del simulateOutage y la telemetría retomada.")
evidence("12_estado_disconnected.png", "Evidencia 6. Estado Disconnected en la lista de dispositivos.", "la lista Devices con un dispositivo en Disconnected y los demás en Connected.")
h2("Logs de los dos códigos de la sustentación")
p("Ambos códigos imprimen el ciclo completo Connecting → Connected → TX #n → comando → Disconnected → reconexión. "
  "El script Python además lo guarda en <font face='DVM'>logs/dc-rack-a-py.log</font>. Extracto esperado del formato:")
story.append(Paragraph(
    "2026-10-01 09:14:02 | INFO | dc-rack-a-py | Connecting | DPS dc-rack-a-py | transporte=MQTT:8883<br/>"
    "2026-10-01 09:14:04 | INFO | dc-rack-a-py | Connected | hub=iotc-….azure-devices.net<br/>"
    "2026-10-01 09:14:04 | INFO | dc-rack-a-py | TX #1 {'tempIntake': 22.4, 'tempExhaust': 34.9, …}<br/>"
    "(formato de ejemplo — la evidencia real es la captura 13)", S["code"]))
evidence("13_log_python_rack_a.png", "Evidencia 7. Log de sesión de rack_a.py (portátil 1).", "la consola con Connecting, Connected, varias líneas TX y la respuesta a un comando.")
evidence("14_log_wokwi_rack_b.png", "Evidencia 8. Monitor serie de Wokwi, Rack B (portátil 2).", "[MQTT] Connected, líneas [TX #n] OK y la recepción de setFanBoost.")
evidence("15_comando_wokwi.png", "Evidencia 9. Respuesta del comando en IoT Central.", "la ventana de historial de comandos con setFanBoost respondido por dc-rack-b-wokwi.")
evidence("16_api_doble_timestamp.png", "Evidencia 10. Orígenes de API con marca de tiempo de fuente y de ingestión.",
         "DEV-05 o DEV-06 con la propiedad lastSourceTimestamp, la telemetría sourceAgeMin y la hora de ingestión del mensaje.")

# =========================================================================== 9 CUATRO DÍAS
h1("Ventana de 4 días no continuos y comparativa")
stats_f = RES / "estadisticas.csv"
if stats_f.is_file():
    st = read_csv(stats_f)
    dias = sorted({r["dia"] for r in st})
    p(f"Días analizados (hora local UTC−5): <b>{', '.join(dias)}</b>. Datos exportados de IoT Central y procesados "
      "con <font face='DVM'>tools/analisis_4dias.py</font>.")
else:
    dias = []
    p("Días analizados: <b>pendiente</b>. Elija cuatro fechas no consecutivas con la flota encendida y exporte "
      "los datos de Data Explorer antes de 30 días (retención de IoT Central). Sugerencia de calendario a partir de "
      "la fecha de este documento: un día de semana normal, un día con mantenimiento programado (dispara pre-alarma "
      "de humo o apertura de puerta), un fin de semana y un día con la prueba de desconexión controlada.", "note")
p("Método: para cada día, dispositivo y variable se calcula máximo, mínimo, promedio y recuento de muestras; la "
  "sumatoria se reporta solo donde tiene significado físico (energía del intervalo → kWh/día, conteos de acceso, "
  "muestras en alarma). El recuento también valida la asincronía: a 15 s DEV-01 debería aportar ≈ 5 760 muestras "
  "diarias; a 5 min DEV-09 ≈ 288; una cifra menor delata huecos.")
KEY = ["tempIntake", "tempExhaust", "humidity", "diffPressure", "currentA", "energyKwh", "tempOutdoor",
       "pm25", "smokeObscuration", "accessDenied"]
if stats_f.is_file():
    rows = [r for r in st if r["variable"] in KEY]
    rows.sort(key=lambda r: (KEY.index(r["variable"]), r["dispositivo"], r["dia"]))
    table(["Variable", "Dispositivo", "Día", "Máx (hora)", "Mín (hora)", "Prom.", "n", "Σ"],
          [[r["variable"], r["dispositivo"], r["dia"], f"{r['max']} ({r['hora_max']})",
            f"{r['min']} ({r['hora_min']})", r["promedio"], r["recuento"], r["sumatoria"] or "—"] for r in rows],
          [.14, .17, .12, .14, .14, .1, .08, .11])
    lec = RES / "lectura.md"
    if lec.is_file():
        h2("Lectura operativa de los extremos")
        for line in lec.read_text(encoding="utf-8").splitlines():
            if line.startswith("- "):
                txt = line[2:].replace("**", "")
                story.append(Paragraph("•&nbsp;&nbsp;" + txt, S["body"]))
    for var in ["tempIntake", "humidity", "diffPressure", "currentA", "tempOutdoor", "pm25"]:
        g = RES / f"grafico_{var}.png"
        if g.is_file():
            figure(g, f"Gráfico — {var}: los 4 días superpuestos por hora local (generado desde el export real).", 0.9)
else:
    table(["Variable", "Dispositivo", "Día 1", "Día 2", "Día 3", "Día 4", "Indicador"],
          [[v, d, "—", "—", "—", "—", i] for v, d, i in [
              ("tempIntake", "Rack A/B/C", "máx / mín / prom / n"), ("humidity", "Rack A/B/C", "máx / mín / prom / n"),
              ("diffPressure", "Pasillo frío", "mín (contención)"), ("currentA", "PDU", "máx / prom"),
              ("energyKwh", "PDU", "Σ = kWh/día"), ("tempOutdoor", "Clima ext.", "máx / mín / prom"),
              ("pm25", "Aire admisión", "máx / prom"), ("smokeObscuration", "Humo", "máx (pre-alarma)"),
              ("accessDenied", "Puerta", "Σ = intentos/día")]],
          [.17, .16, .1, .1, .1, .1, .27])
    h2("Guía de lectura operativa (qué explicar de cada extremo)")
    bullets(["<b>tempIntake máx.</b> ¿Coincide con la hora de mayor carga de TI o con temperatura exterior alta? Si superó 27 °C, R01 debe figurar en el bloque de alertas de ese día.",
             "<b>diffPressure mín.</b> Valores bajo 2 Pa corresponden a puerta de contención abierta (mantenimiento, ingreso de personal); correlacionar con doorOpen de DEV-10.",
             "<b>Σ energyKwh.</b> Energía de TI de la fila por día; su diferencia entre días hábiles y fin de semana mide la variación de carga.",
             "<b>tempOutdoor mín.</b> Solo las madrugadas de Bucaramanga bajan de 18 °C: cuantifica las horas reales de free-cooling.",
             "<b>pm25 máx.</b> Si supera 35,4 µg/m³, el economizador debió cerrarse (R13); típicamente en horas pico de tráfico.",
             "<b>Recuento.</b> Un recuento menor al esperado por la cadencia es la medida numérica de la desconexión."])
for i in range(4):
    evidence(f"0{6 + i}_data_explorer_dia{i + 1}.png", f"Evidencia {11 + i}. Data Explorer — día {i + 1}"
             + (f" ({dias[i]})" if i < len(dias) else "") + ".",
             f"el gráfico de IoT Central del día {i + 1} con las variables indispensables (tempIntake y humidity de A/B/C) y la fecha visible.",
             max_h=8.5 * cm)
evidence("05_alertas_4dias.png", "Evidencia 15. Rules disparadas en la ventana de 4 días.", "el historial de alertas con fecha, Rule y dispositivo.")

# =========================================================================== 10 CONTROL ROOM
h1("Dashboard tipo cuarto de control")
p("Dashboard de aplicación con identidad propia (logo y nombre del escenario, no el nombre genérico de la app). "
  "La figura 4 es la maqueta de diseño que guía la construcción de los tiles; la evidencia 16 es la captura real.")
figure(ASSETS / "maqueta_control_room.png", "Figura 4. Maqueta de diseño del control room (no es captura de IoT Central).", 0.95)
table(["Requisito del enunciado (sección 7)", "Tile en IoT Central", "Fuente"], [
    ["Logo y nombre del escenario", "Appearance (logo de la app) + tile Imagen con logo y Label «Nodo Chicamocha DC · Control Room»", "docs/assets/logo.png"],
    ["Estado de la flota Connected/Disconnected/Unassociated", "Tile de estado sobre la lista de dispositivos (o grupos de dispositivos filtrados por estado de conexión, según lo que ofrezca la versión de la app)", "Estado de conexión de los 10"],
    ["≥ 4 gráficos de variables indispensables", "Line chart: tempIntake A/B/C · humidity A/B/C · diffPressure · currentA", "DEV-01…04, 09"],
    ["KPIs numéricos", "KPI / Last known value: máx y mín del día de tempIntake, Σ energyKwh, último pm25", "DEV-01…03, 06, 09"],
    ["Bloque de alertas", "Tile de alertas / historial de eventos con las Rules disparadas", "R01–R14"],
    ["Mapa o esquema de zonas", "Tile Imagen con mapa_zonas.png", "Figura 2"],
    ["Mapa térmico de racks (escenario 5.2)", "Heat map / KPI de tempIntake y tempExhaust de A, B y C", "DEV-01…03"],
    ["Alarmas de agua, humo y energía (5.2)", "Last known value con formato condicional: leakDetected, smokeAlarm, breakerClosed", "DEV-07, 08, 09"],
], [.32, .48, .2])
evidence("03_dashboard_control_room.png", "Evidencia 16. Dashboard del control room en IoT Central.",
         "el dashboard completo en una sola pantalla: logo, estado de flota, cuatro gráficos, KPIs, alertas y mapa de zonas.", max_h=12 * cm)
evidence("02_dispositivos.png", "Evidencia 17. Lista de los 10 dispositivos con su plantilla y estado.", "Devices con los 10 IDs del catálogo, su plantilla y el estado de conexión.")

# =========================================================================== 11 SUSTENTACIÓN
h1("Guion de la sustentación presencial")
table(["Min.", "Actividad", "Equipo"], [
    ["0–2", "Escenario, cliente y arquitectura (figura 1). Por qué cada origen es distinto (tabla del catálogo).", "Proyector"],
    ["2–4", "Digital Twin: plantilla RackThermal, propiedades escribibles, comandos; Rack C simulado como gemelo de referencia.", "IoT Central"],
    ["4–6", "Portátil 1: <font face='DVM'>python devices/dev01_rack_a_python_mqtt/rack_a.py</font> → Connecting / Connected / TX en vivo.", "Portátil 1"],
    ["6–8", "Portátil 2: Wokwi Rack B ▶ → Connected; mover el slider del DHT22 sobre 27 °C → LED OVERTEMP y valor en Central; comando setFanBoost → relé.", "Portátil 2"],
    ["8–10", "Desconexión controlada: simulateOutage 120 s sobre DEV-01 → Disconnected, hueco, reconexión.", "IoT Central"],
    ["10–12", "Control room y navegación de un gráfico de los 4 días no continuos; comparativa y lectura de extremos.", "IoT Central"],
    ["12–15", "Preguntas: umbrales, datasheets, limitaciones de IoT Central.", "—"],
], [.08, .76, .16])
h2("Plan de contingencia")
bullets(["Si falla la red del salón: compartir datos del celular (el script usa 8883; si está bloqueado, ejecutar DEV-04, que va por 443).",
         "Si Wokwi no conecta (cola del simulador gratuito): usar DEV-10 (segunda instancia Wokwi) o DEV-07 (paho) en el portátil 2.",
         "Si las API (DEV-05/06) no responden por cuota: se muestra la evidencia histórica; el enunciado admite sustituir en vivo por el par Python + Wokwi.",
         "Llevar .env y secrets.h en una memoria USB (nunca en el repositorio) y el hub ya resuelto en la caché de DPS."])
h2("Preguntas probables y respuesta preparada")
table(["Pregunta", "Respuesta breve"], [
    ["¿Por qué 27 °C y no otro valor?", "Límite superior del rango recomendado ASHRAE A1 para aire de entrada; 32 °C es el máximo permisible A1 (crítico)."],
    ["¿Por qué promedio de 5 min en R01?", "El DHT22 tiene ±0,5 °C y ruido; se evita la alerta por una muestra aislada sin perder reacción ante una tendencia real."],
    ["¿Por qué el PDU no aparece Connected?", "HTTP no mantiene sesión; IoT Central recibe la telemetría pero no un evento de conexión persistente. Es una limitación del protocolo, documentada."],
    ["¿Cómo se protege la clave?", "Solo variables de entorno / secrets.h fuera de Git; la clave del dispositivo se deriva por HMAC de la del grupo y el token SAS expira en 1 h."],
    ["¿Qué pasa si el dispositivo se desconecta?", "El SDK y paho reintentan con backoff; las muestras del hueco no se reenvían (se documenta como pérdida, visible en el recuento)."],
    ["¿Diferencia entre Rack A, B y C?", "Mismo gemelo; A es Python con perfil físico, B es firmware en ESP32 con sensores simulados y actuador, C es el simulador aleatorio de la plataforma."],
], [.34, .66])

# =========================================================================== 12 LIMITACIONES
h1("Limitaciones percibidas de IoT Central")
bullets([
    "<b>Retención:</b> los datos consultables en Data Explorer tienen retención limitada (30 días); para la ventana de 4 días hay que exportar antes o configurar Data Export continuo a Blob Storage.",
    "<b>Simulador nativo:</b> genera valores aleatorios dentro del esquema y con cadencia fija de la plataforma; no reproduce perfiles físicos ni correlaciones (por eso Rack C se usa solo como referencia).",
    "<b>Rules:</b> condiciones sobre una sola plantilla y ventanas de agregación predefinidas; no admite lógica entre dispositivos (p. ej. «dP bajo Y puerta abierta») sin un servicio externo.",
    "<b>Acciones:</b> una Rule no ejecuta un comando directamente; se requiere Power Automate/Logic Apps o un webhook propio.",
    "<b>HTTP:</b> sin comandos en tiempo real ni estado Connected persistente para dispositivos que publican por REST.",
    "<b>Dashboards:</b> tipos de tile fijos, sin estadística personalizada por día; por eso la comparativa de 4 días se calcula fuera (analisis_4dias.py).",
    "<b>Costo y cuotas:</b> la facturación por dispositivo y por mensajes limita la cadencia en producción; 15 s es razonable para la demo, no necesariamente para 300 racks.",
])

# =========================================================================== 13 REPO
h1("Repositorio y seguridad")
story.append(Paragraph(
    "nodo-chicamocha-dc/<br/>"
    "├─ README.md · requirements.txt · .env.example · .gitignore<br/>"
    "├─ common/ iotc_common.py (DPS REST, SAS, derivación de clave) · sdk_device.py (SDK + simulateOutage)<br/>"
    "├─ templates/ 8 × DTDL v2 (.json) · gen_dtdl.py<br/>"
    "├─ devices/<br/>"
    "│&nbsp;&nbsp;├─ dev01_rack_a_python_mqtt/ rack_a.py<br/>"
    "│&nbsp;&nbsp;├─ dev02_rack_b_wokwi/ sketch.ino · diagram.json · libraries.txt · secrets.h.example<br/>"
    "│&nbsp;&nbsp;├─ dev03_rack_c_simulado/ README.md (pasos en Central)<br/>"
    "│&nbsp;&nbsp;├─ dev04_pasillo_python_mqttws/ aisle.py<br/>"
    "│&nbsp;&nbsp;├─ dev05_clima_openweather/ weather_bridge.py<br/>"
    "│&nbsp;&nbsp;├─ dev06_aire_openmeteo/ airquality_bridge.py<br/>"
    "│&nbsp;&nbsp;├─ dev07_agua_paho_mqtt/ leak_paho.py<br/>"
    "│&nbsp;&nbsp;├─ dev08_humo_node_amqp_replay/ replay.js · package.json · data/humo_historico.csv<br/>"
    "│&nbsp;&nbsp;├─ dev09_pdu_http_rest/ pdu_rest.py<br/>"
    "│&nbsp;&nbsp;└─ dev10_puerta_wokwi/ sketch.ino · diagram.json · secrets.h.example<br/>"
    "├─ tools/ provision.py · analisis_4dias.py<br/>"
    "├─ docs/ catalogo.py (fuente única) · diagramas.py · build_pdf.py · assets/<br/>"
    "├─ evidencias/ (capturas reales) · datos_4dias/ (exports de Central)", S["code"]))
bullets(["<b>Sin secretos en claro:</b> ID scope y clave de grupo solo en <font face='DVM'>.env</font>; en Wokwi en "
         "<font face='DVM'>secrets.h</font>; ambos en .gitignore. Los ejemplos del repo usan marcadores.",
         "<b>Claves por dispositivo:</b> derivadas por HMAC-SHA256(clave de grupo, deviceId); comprometer un dispositivo no expone al grupo.",
         "<b>TLS:</b> validación del certificado del servidor en Python y Node (almacén del sistema). En Wokwi se puede cargar DigiCert Global Root G2 en secrets.h; si se deja vacío, el sketch usa setInsecure() y lo anuncia en el monitor serie (solo aceptable en el simulador).",
         "<b>Perfil CSV de DEV-08:</b> es un perfil de prueba de 24 h construido sobre los rangos de UL 268, declarado como tal; no se presenta como registro histórico de un incidente real."])
h2("Ejecución rápida")
story.append(Paragraph(
    "pip install -r requirements.txt&nbsp;&nbsp;&nbsp;# Python ≥ 3.10<br/>"
    "cp .env.example .env&nbsp;&nbsp;&nbsp;# completar ID scope y clave de grupo<br/>"
    "python devices/dev01_rack_a_python_mqtt/rack_a.py<br/>"
    "python devices/dev04_pasillo_python_mqttws/aisle.py<br/>"
    "python devices/dev05_clima_openweather/weather_bridge.py<br/>"
    "python devices/dev06_aire_openmeteo/airquality_bridge.py<br/>"
    "python devices/dev07_agua_paho_mqtt/leak_paho.py<br/>"
    "python devices/dev09_pdu_http_rest/pdu_rest.py<br/>"
    "cd devices/dev08_humo_node_amqp_replay &amp;&amp; npm install &amp;&amp; npm start<br/>"
    "python tools/provision.py dc-rack-b-wokwi \"dtmi:chicamochadc:RackThermal;1\"&nbsp;&nbsp;# → secrets.h de Wokwi<br/>"
    "python tools/analisis_4dias.py datos_4dias/*.csv --dias D1 D2 D3 D4<br/>"
    "python docs/build_pdf.py", S["code"]))

# =========================================================================== ANEXOS
h1("Anexo A · Despliegue paso a paso en IoT Central")
steps = [
    ("Crear la aplicación", "portal de IoT Central → New application → plantilla Custom; nombre «Nodo Chicamocha DC»; plan Standard 0 o el de la suscripción de estudiante."),
    ("Identidad visual", "Customization → Appearance: cargar docs/assets/logo.png como logo y como icono; colores #0F2A44 / #1C8C8C."),
    ("Plantillas", "Device templates → + New → IoT device → Import a model → cada templates/*.json. Crear la vista Overview y la de Properties; Publish."),
    ("Grupo de conexión", "Permissions → Device connection groups → SAS-IoT-Devices: copiar ID scope y clave primaria al .env (nunca al repo)."),
    ("Dispositivo simulado", "Devices → + New → plantilla Rack térmico, ID dc-rack-c-sim, Simulate = Yes."),
    ("Dispositivos reales", "No es necesario crearlos: al ejecutar cada código, el DPS con payload modelId los registra y asocia a su plantilla. Verificar que ninguno quede Unassociated."),
    ("Wokwi", "Ejecutar tools/provision.py para DEV-02 y DEV-10; pegar el resultado en secrets.h de cada proyecto Wokwi (pestaña nueva de archivo)."),
    ("Rules", "Rules → + New: crear R01–R14 con la condición, agregación y acción de la tabla de la sección 7."),
    ("Dashboard", "Dashboards → + New «Control Room»: tiles según la tabla de la sección 10."),
    ("Ventana de 4 días", "Dejar la flota en segundo plano (VM o equipo encendido) y registrar las fechas; exportar desde Data Explorer cada día elegido a datos_4dias/."),
    ("Documento", "Guardar capturas en evidencias/ con los nombres de evidencias/README.md; ejecutar analisis_4dias.py y build_pdf.py."),
]
table(["#", "Paso", "Detalle"], [[i + 1, a, b] for i, (a, b) in enumerate(steps)], [.05, .2, .75])

h1("Anexo B · Trazabilidad con la rúbrica")
table(["Indicador (peso)", "Dónde se evidencia"], [
    ["IoT Template, setup + test (15 %)", "Sección 4 (plantillas, propiedades, comandos), sección 7 (Rules), evidencias 1–3; identidad visual en Anexo A paso 2."],
    ["Datos, Digital Twin y arquitectura (20 %)", "Secciones 3, 5 y 6: diagrama con telecomunicaciones, catálogo de 10, datasheets y rangos."],
    ["Heterogeneidad de orígenes (20 %)", "Sección 5.1 (por qué es distinto) y sección 8 (asincronía, desconexión, operación en línea)."],
    ["Ventana de 4 días y comparativa (15 %)", "Sección 9: tabla máx/mín/prom/n/Σ, lectura operativa y capturas de los 4 días."],
    ["Control room y documento (15 %)", "Sección 10, tablas de parámetros (sección 6), historial de versiones, sección 13 (repo limpio)."],
    ["Sustentación y dos códigos en vivo (15 %)", "Sección 11: guion, contingencia y respuestas preparadas; DEV-01 + DEV-02."],
], [.33, .67])

h1("Anexo C · Referencias")
bullets([
    "Microsoft Learn — Documentación de Azure IoT Central: https://learn.microsoft.com/es-es/azure/iot-central/",
    "Microsoft Learn — Comunicación con IoT Hub mediante MQTT, AMQP y HTTPS; Device Provisioning Service (registro con clave simétrica y payload modelId).",
    "Azure IoT SDK para Python (azure-iot-device 2.x) y para Node.js (azure-iot-device, azure-iot-device-amqp, azure-iot-provisioning-device).",
    "Digital Twins Definition Language (DTDL) v2 — especificación de interfaces, telemetría, propiedades y comandos.",
    "ASHRAE TC 9.9 — Thermal Guidelines for Data Processing Environments (clases A1–A4, rango recomendado 18–27 °C).",
    "ANSI/TIA-942 — Telecommunications Infrastructure Standard for Data Centers (uso académico).",
    "UL 268 — Smoke Detectors for Fire Alarm Systems (rango de sensibilidad 0,5–4,0 %/ft).",
    "Hojas de datos: Sensirion SHT45, SHT31 y SDP810; Analog Devices/Maxim DS18B20; Aosong AM2302 (DHT22); Plantower PMS5003; Eastron SDM630-Modbus V2; Davis Instruments Vantage Pro2 (6152); NXP MFRC522.",
    "APIs: OpenWeather Current Weather Data 2.5; Open-Meteo Forecast API; Open-Meteo Air Quality API (Copernicus CAMS).",
    "Wokwi — ESP32 Wi-Fi Networking: https://docs.wokwi.com/guides/esp32-wifi",
])


def build():
    doc = Doc(OUT)
    doc.multiBuild(story)
    print("PDF:", OUT)


if __name__ == "__main__":
    build()
