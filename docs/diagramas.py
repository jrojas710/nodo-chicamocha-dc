#!/usr/bin/env python3
"""diagramas.py — genera logo, arquitectura de referencia, mapa de zonas, maqueta del
control room y cronograma de cadencias (docs/assets/*.png). Todo sale de catalogo.py."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalogo import DEVICES  # noqa: E402

A = HERE / "assets"
A.mkdir(exist_ok=True)
NAVY, TEAL, AMBER, RED, GRAY, LIGHT, INK = "#0F2A44", "#1C8C8C", "#E0A100", "#B3261E", "#6B7785", "#EEF3F7", "#1B1F24"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

PROTO_COLOR = {"MQTT 8883": TEAL, "MQTT-WS 443": "#5B6CC7", "AMQPS 5671": "#8E5BB5",
               "HTTPS 443": AMBER, "Interno": GRAY}
DEV_PROTO = {"01": "MQTT 8883", "02": "MQTT 8883", "03": "Interno", "04": "MQTT-WS 443",
             "05": "MQTT 8883", "06": "MQTT 8883", "07": "MQTT 8883", "08": "AMQPS 5671",
             "09": "HTTPS 443", "10": "MQTT 8883"}


def box(ax, x, y, w, h, text, fc=LIGHT, ec=NAVY, fs=8, tc=INK, bold=False, r=0.02, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def logo():
    fig, ax = plt.subplots(figsize=(4, 4), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(Circle((0.5, 0.5), 0.48, fc=NAVY))
    ax.add_patch(Circle((0.5, 0.5), 0.43, fc="none", ec=TEAL, lw=3))
    # cañón del Chicamocha (silueta)
    ax.add_patch(Polygon([[0.12, 0.40], [0.28, 0.62], [0.40, 0.48], [0.50, 0.70], [0.62, 0.50],
                          [0.74, 0.64], [0.88, 0.40]], closed=True, fc=TEAL, alpha=.55))
    # tres racks A/B/C
    for i, x in enumerate([0.31, 0.45, 0.59]):
        ax.add_patch(Rectangle((x, 0.22), 0.10, 0.30, fc="white", ec=NAVY, lw=1.5))
        for k in range(4):
            ax.add_patch(Rectangle((x + 0.015, 0.25 + k * 0.065), 0.07, 0.04, fc=LIGHT, ec="none"))
            ax.add_patch(Circle((x + 0.075, 0.27 + k * 0.065), 0.008, fc=[TEAL, AMBER, TEAL][i]))
    ax.text(0.5, 0.80, "NODO", ha="center", color="white", fontsize=18, fontweight="bold")
    ax.text(0.5, 0.12, "CHICAMOCHA DC", ha="center", color="white", fontsize=11, fontweight="bold")
    fig.savefig(A / "logo.png", transparent=True, bbox_inches="tight"); plt.close(fig)


def arquitectura():
    fig, ax = plt.subplots(figsize=(8.3, 10.2), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 124); ax.axis("off")
    layers = [(92, 31, "1 · CAPA DE DISPOSITIVO (10 orígenes de envío distintos)"),
              (64, 26, "2 · CAPA DE RED / TELECOMUNICACIONES"),
              (29, 33, "3 · CAPA DE PLATAFORMA (Azure)"),
              (1, 26, "4 · CAPA DE OPERACIÓN")]
    for y, h, t in layers:
        ax.add_patch(Rectangle((0, y), 100, h, fc="#F7F9FB", ec="#C9D3DD", lw=1))
        ax.text(1.5, y + h - 2.3, t, fontsize=9, fontweight="bold", color=NAVY)
    # Dispositivos: 2 filas de 5
    short = {"01": ("Rack A", "Python SDK"), "02": ("Rack B", "Wokwi ESP32 #1"),
             "03": ("Rack C", "Digital Twin simulado"), "04": ("Pasillo frío", "Python MQTT-WS"),
             "05": ("Clima exterior", "OpenWeather (≈Atlas)"), "06": ("Aire de admisión", "API Open-Meteo AQ"),
             "07": ("Agua bajo piso", "paho-mqtt crudo"), "08": ("Humo / techo", "Replay CSV Node"),
             "09": ("PDU fila 1", "Puente HTTP/REST"), "10": ("Puerta sala", "Wokwi ESP32 #2")}
    pos = {}
    for i, d in enumerate(DEVICES):
        row, col = divmod(i, 5)
        x, y = 1.8 + col * 19.6, 108 - row * 14
        proto = DEV_PROTO[d["n"]]
        z, o = short[d["n"]]
        itv = d["intervalo"].replace("Fija de la plataforma", "cadencia plataforma").replace("Evento + latido", "evento + latido")
        box(ax, x, y, 18.4, 11.5, f"DEV-{d['n']} · {z}\n{o}\n{itv}", fc="white",
            ec=PROTO_COLOR[proto], fs=6.4, lw=1.8)
        pos[d["n"]] = ((x - 0.6) if row == 0 else (x + 9.2), y if row == 1 else y + 0.0, row)
    # Red
    box(ax, 2, 75, 30, 9.5, "LAN sala técnica\nEthernet 1 GbE (VM, gateway Modbus)\nWi-Fi WPA2-Enterprise 2.4 GHz (ESP32)",
        fc="white", fs=6.8)
    box(ax, 35, 75, 30, 9.5, "Firewall / NAT del edificio\nsalida TCP 8883 · 443 · 5671\nDNS + NTP (SAS exige hora UTC)",
        fc="white", fs=6.8)
    box(ax, 68, 75, 30, 9.5, "ISP urbano fibra FTTH (principal)\n+ router 4G/LTE (respaldo)\nInternet → Azure (TLS 1.2)",
        fc="white", fs=6.8)
    for x0, x1 in ((32, 35), (65, 68)):
        ax.annotate("", (x1, 79.7), (x0, 79.7), arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.3))
    # leyenda de protocolos
    lx = 3
    for p, c in PROTO_COLOR.items():
        ax.add_patch(Rectangle((lx, 67), 3, 2, fc=c)); ax.text(lx + 3.6, 68, p, va="center", fontsize=6.0)
        lx += 11.5
    # líneas dispositivo → red
    for n, (x, y, row) in pos.items():
        if n == "03":
            continue
        if row == 0:   # baja por el canal entre cajas
            ax.plot([x + 9.8, x + 9.8, x + 0.0 + 0.0], [y, y - 1.2, y - 1.2], color=PROTO_COLOR[DEV_PROTO[n]], lw=0)
            ax.plot([x, x], [y + 5.7, 86.5], color=PROTO_COLOR[DEV_PROTO[n]], lw=1.1, alpha=.85)
        else:
            ax.plot([x, x], [y, 86.5], color=PROTO_COLOR[DEV_PROTO[n]], lw=1.1, alpha=.85)
    ax.plot([2, 98], [86.5, 86.5], color=GRAY, lw=.8, ls=":")
    ax.annotate("", (17, 84.5), (17, 86.5), arrowprops=dict(arrowstyle="->", color=GRAY))
    # Plataforma
    box(ax, 3, 42, 22, 12, "Azure DPS\nglobal.azure-devices-\nprovisioning.net\nID scope + SAS de grupo\npayload {modelId}",
        fc="white", fs=6.6)
    box(ax, 29, 42, 22, 12, "IoT Hub gestionado\n(interno de Central)\nMQTT · MQTT-WS\nAMQP · HTTPS\nTLS 1.2 · SAS", fc="white", fs=6.6)
    box(ax, 55, 31, 42, 25, "", fc="#E6F2F2", ec=TEAL, lw=1.6)
    ax.text(76, 53, "Azure IoT Central · app Nodo Chicamocha DC", ha="center", fontsize=7.6, fontweight="bold", color=NAVY)
    box(ax, 57, 41, 18.5, 9.5, "Device Templates\n(Digital Twin DTDL v2)\n8 interfaces ;1", fc="white", fs=6.4)
    box(ax, 77, 41, 18.5, 9.5, "Twin: propiedades\nescribibles · comandos\nestado Connected", fc="white", fs=6.4)
    box(ax, 57, 32.5, 38.5, 7, "Telemetría + Data Explorer (30 días)\nsimulador nativo DEV-03",
        fc="white", fs=6.3)
    ax.annotate("", (3 + 11, 54), (68 + 15, 75), arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.3,
                                                                  connectionstyle="arc3,rad=-0.15"))
    ax.text(40, 62.5, "① registro DPS (hub asignado)", fontsize=6.4, color=NAVY)
    ax.annotate("", (29, 48), (25, 48), arrowprops=dict(arrowstyle="<->", color=NAVY, lw=1.2))
    ax.annotate("", (55, 48), (51, 48), arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2))
    ax.annotate("", (40, 54), (83, 75), arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.6,
                                                         connectionstyle="arc3,rad=0.1"))
    ax.text(58, 58.5, "② telemetría / twin / comandos (TLS)", fontsize=6.4, color=TEAL)
    # Operación
    items = [("Views por\nplantilla\n(operador)", 2), ("Rules R01–R14\n7 categorías\nsin mezclar umbrales", 21.5),
             ("Dashboard\nControl Room\n(logo, KPIs, mapa)", 41), ("Acciones:\ncorreo NOC ·\nwebhook", 60.5),
             ("Export CSV →\nanalisis_4dias.py\n(máx/mín/prom…)", 80)]
    for t, x in items:
        box(ax, x, 5, 17.5, 13, t, fc="white", ec=NAVY, fs=6.6)
        ax.annotate("", (x + 8.75, 18), (76, 31), arrowprops=dict(arrowstyle="->", color=GRAY, lw=.8))
    fig.savefig(A / "arquitectura.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


def mapa_zonas():
    fig, ax = plt.subplots(figsize=(8.3, 5.4), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 64); ax.axis("off"); ax.set_aspect("equal")
    ax.add_patch(Rectangle((2, 4), 70, 54, fc="#FBFCFD", ec=NAVY, lw=2))
    ax.text(4, 55, "SALA BLANCA · planta 1", fontsize=8, fontweight="bold", color=NAVY)
    ax.add_patch(Rectangle((10, 26), 54, 10, fc="#DDEFF7", ec=TEAL, lw=1.2, ls="--"))
    ax.text(37, 31, "PASILLO FRÍO (contención)  ◉ DEV-04", ha="center", fontsize=7, color=NAVY)
    for i, (lab, n) in enumerate([("Rack A", "01 · Python"), ("Rack B", "02 · Wokwi"), ("Rack C", "03 · Simulado")]):
        x = 12 + i * 18
        ax.add_patch(Rectangle((x, 36.5), 14, 9, fc=NAVY, ec="none"))
        ax.text(x + 7, 41, f"{lab}\nDEV-{n}", ha="center", va="center", color="white", fontsize=6.5)
    ax.add_patch(Rectangle((10, 46), 54, 6, fc="#F8E3DF", ec=RED, lw=1, ls="--"))
    ax.text(37, 49, "PASILLO CALIENTE (tempExhaust)", ha="center", fontsize=6.8, color=RED)
    ax.add_patch(Rectangle((12, 18), 14, 6, fc=AMBER, ec="none"))
    ax.text(19, 21, "PDU fila 1\nDEV-09", ha="center", va="center", fontsize=6.5)
    ax.plot([6, 68, 68, 6, 6], [8, 8, 54, 54, 8], color="#3B7DD8", lw=1, ls=(0, (1, 2)))
    ax.text(30, 10, "cable de fuga bajo piso · DEV-07 (zonas 1-2-3)", fontsize=6.5, color="#3B7DD8")
    ax.plot(60, 20, marker="o", ms=12, color=RED); ax.text(60, 15.5, "Humo/techo\nDEV-08", ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((71, 26), 2, 8, fc=GRAY)); ax.text(75, 30, "Puerta\nDEV-10", fontsize=6.5, va="center")
    ax.add_patch(Rectangle((80, 38), 18, 18, fc="#F1F5F1", ec=GRAY, lw=1))
    ax.text(89, 53, "CUBIERTA", ha="center", fontsize=7, fontweight="bold", color=NAVY)
    ax.text(89, 46, "Clima ext.\nDEV-05", ha="center", fontsize=6.5)
    ax.text(89, 40.5, "Toma free-cooling\nDEV-06", ha="center", fontsize=6.3)
    ax.add_patch(Rectangle((80, 8), 18, 18, fc="#F1F5F1", ec=GRAY, lw=1))
    ax.text(89, 17, "NOC / Control room\n(Dashboard\nIoT Central)", ha="center", va="center", fontsize=6.5)
    fig.savefig(A / "mapa_zonas.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


def maqueta_control_room():
    fig, ax = plt.subplots(figsize=(8.3, 5.6), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 68); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 100, 68, fc="#F4F6F8"))
    ax.add_patch(Rectangle((0, 60), 100, 8, fc=NAVY))
    ax.text(10, 64, "NODO CHICAMOCHA DC · Control Room", color="white", fontsize=10, fontweight="bold", va="center")
    ax.add_patch(Circle((5, 64), 3, fc=TEAL))
    def tile(x, y, w, h, title, body="", fc="white"):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#CFD8E0"))
        ax.text(x + 1, y + h - 1.6, title, fontsize=6.2, fontweight="bold", color=NAVY, va="top")
        ax.text(x + w / 2, y + (h - 3) / 2, body, fontsize=6, ha="center", va="center", color=GRAY)
    tile(1, 48, 23, 11, "Estado de la flota", "Connected · Disconnected\n· Unassociated\n(tile Device count)")
    tile(25, 48, 24, 11, "Mapa térmico racks A/B/C", "último tempIntake /\ntempExhaust por rack\n(tile heat map / KPI)")
    tile(50, 48, 24, 11, "Alarmas agua · humo · energía", "leakDetected · smokeAlarm\nbreakerClosed (último valor)")
    tile(75, 48, 24, 11, "KPIs del día", "máx/mín tempIntake\nkWh del día (Σ energyKwh)")
    for i, t in enumerate(["tempIntake A/B/C", "humidity A/B/C", "diffPressure pasillo", "currentA PDU"]):
        tile(1 + i * 24.7, 26, 23.9, 21, t, "gráfico de líneas\n(ventana seleccionable)")
    tile(1, 1, 36, 24, "Mapa de zonas (imagen)", "mapa_zonas.png\ndispositivo ↔ lugar")
    tile(38, 1, 30, 24, "Clima y aire exterior", "tempOutdoor · dewPoint\npm25 · aqi · free-cooling")
    tile(69, 1, 30, 24, "Alertas (Rules disparadas)", "lista de alertas\nventana de 4 días")
    ax.text(99, 0.3, "MAQUETA DE DISEÑO — no es captura de IoT Central", ha="right", va="bottom",
            fontsize=6, color=RED, style="italic")
    fig.savefig(A / "maqueta_control_room.png", bbox_inches="tight", facecolor="white"); plt.close(fig)


def cadencias():
    fig, ax = plt.subplots(figsize=(8.3, 3.4), dpi=200)
    horizon = 1800
    ys = []
    for i, d in enumerate(DEVICES):
        y = len(DEVICES) - i
        ys.append((y, f"DEV-{d['n']} · {d['intervalo']}"))
        s = d["intervalo_s"]
        if s is None:
            ax.text(10, y, "cadencia fijada por IoT Central", va="center", fontsize=6.5, color=GRAY)
            continue
        ev = "Evento" in d["intervalo"]
        xs = list(range(0, horizon + 1, s))
        if d["n"] == "01":   # nodo en vivo #1: hueco controlado y reconexión
            xs = [x for x in xs if not 900 <= x <= 1140]
        ax.vlines(xs, y - .3, y + .3, color=PROTO_COLOR[DEV_PROTO[d["n"]]], lw=1.3)
        if ev:
            for x in (430, 1210):
                ax.plot(x, y, marker="v", color=RED, ms=5)
    ax.plot(1500, 1, alpha=0)
    ax.add_patch(Rectangle((900, 9.55), 240, 0.9, color=RED, alpha=.12))
    ax.text(1020, 10.62, "hueco DEV-01: simulateOutage 240 s → reconexión", ha="center", fontsize=6.3, color=RED)
    ax.set_yticks([y for y, _ in ys]); ax.set_yticklabels([t for _, t in ys], fontsize=6.6)
    ax.set_xlim(-10, horizon + 10); ax.set_xlabel("segundos (ventana ilustrativa de 30 min) · ▼ = envío por evento", fontsize=7)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title("Diseño de asincronía de la flota (cadencias configuradas en código)", loc="left", fontsize=8.5, color=NAVY, pad=16)
    fig.tight_layout(); fig.savefig(A / "cadencias.png", facecolor="white"); plt.close(fig)


if __name__ == "__main__":
    logo(); arquitectura(); mapa_zonas(); maqueta_control_room(); cadencias()
    print("assets:", sorted(p.name for p in A.iterdir()))
