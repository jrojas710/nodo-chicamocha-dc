#!/usr/bin/env python3
"""
backfill_historico.py — Carga una ventana de 4 días NO continuos en IoT Central
mediante REPLAY HISTÓRICO (origen aceptado por el enunciado: "replay de CSV o histórico").

Cada mensaje lleva la propiedad de sistema `iothub-creation-time-utc` con la marca de
tiempo ORIGINAL de la muestra, de modo que IoT Central la grafica en su fecha real,
y el campo `replay: true` para que quede trazable que es una recarga.

Qué se envía por dispositivo:
  * DEV-05 clima exterior  -> datos REALES horarios de Bucaramanga (Open-Meteo, past_days)
  * DEV-06 calidad de aire -> datos REALES horarios (Open-Meteo Air Quality / CAMS)
  * DEV-01, 04, 07, 08, 09 -> el mismo modelo de señal de sus scripts, re-ejecutado para
    esas fechas con paso de 5 min (declarado en el documento como replay generado).
El simulador nativo (DEV-03) y los Wokwi (DEV-02, DEV-10) no se recargan.

Uso:  python tools/backfill_historico.py --dias 2026-09-21 2026-09-23 2026-09-25 2026-09-27
Requiere IOTC_ID_SCOPE e IOTC_GROUP_KEY en el entorno.  Versión: 1.0.0
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from iotc_common import (HTTP_API, clamp, dew_point, dps_register_rest,  # noqa: E402
                         generate_sas, get_device_key, load_dotenv, require_env,
                         setup_logging)

TZ = timezone(timedelta(hours=-5))
LAT, LON = 7.1193, -73.1227
STEP = timedelta(minutes=5)

MODELS = {
    "dc-rack-a-py": "dtmi:l0oxnytlx:nvfo9igr;1",
    "dc-aisle-cold-pyws": "dtmi:r2siy0a3m:l6ditz2k;1",
    "dc-weather-owm": "dtmi:mktff6a:qgkhn7v7;1",
    "dc-airq-api": "dtmi:yzsvlqec:virbcjtb;1",
    "dc-leak-paho": "dtmi:h45esikou:rupkcvyp;1",
    "dc-smoke-replay": "dtmi:orujaybg:tcp7bhfw;1",
    "dc-pdu-rest": "dtmi:f9elawiv:mtvnrf8v;1",
}


def diurnal(h, base, amp, peak=15.0):
    return base + amp * math.cos((h - peak) / 24.0 * 2 * math.pi)


# ------------------------------------------------------------- series por dispositivo
def rack_a(t):
    h = t.hour + t.minute / 60
    intake = round(clamp(diurnal(h, 22.5, 1.8) + random.gauss(0, .15), 18, 30), 2)
    ex = round(clamp(intake + diurnal(h, 12, 2) + random.gauss(0, .3) - .3, 26, 46), 2)
    hr = round(clamp(diurnal(h, 45, 5, 5) + random.gauss(0, .5), 30, 58), 1)
    return {"tempIntake": intake, "tempExhaust": ex, "humidity": hr,
            "deltaT": round(ex - intake, 2), "overTemp": intake > 27}


def aisle(t):
    h = t.hour + t.minute / 60
    ta = round(clamp(diurnal(h, 20.5, 1.2) + random.gauss(0, .1), 17, 27), 2)
    hr = round(clamp(diurnal(h, 46, 4, 5) + random.gauss(0, .4), 30, 60), 1)
    dp = 4.5 + random.gauss(0, .35)
    if random.random() < .04:
        dp = random.uniform(.3, 1.6)
    return {"tempAisle": ta, "humidity": hr, "diffPressure": round(clamp(dp - .2, 0, 10), 2),
            "dewPoint": dew_point(ta, hr)}


def pdu(t, state={"tot": 0.0}):
    h = t.hour + t.minute / 60
    i = clamp(diurnal(h, 16, 4) + random.gauss(0, .6), 2, 32)
    v = clamp(127 + random.gauss(0, 1.5), 114, 140)
    pf = clamp(.95 + random.gauss(0, .015), .8, 1)
    kw = 3 * v * i * pf / 1000
    e = kw * 300 / 3600
    state["tot"] += e
    return {"voltageV": round(v, 1), "currentA": round(i, 2), "powerFactor": round(pf, 3),
            "activePowerKw": round(kw, 3), "energyKwh": round(e, 4),
            "energyTotalKwh": round(state["tot"], 3), "breakerClosed": True,
            "loadPercent": round(100 * i / 32, 1)}


def leak(t):
    return {"leakDetected": False, "leakZone": 0,
            "floorHumidity": round(clamp(48 + random.gauss(0, .8), 30, 95), 1),
            "eventReason": "heartbeat"}


SMOKE = None


def smoke(t):
    global SMOKE
    if SMOKE is None:
        import csv
        p = Path(__file__).resolve().parents[1] / "devices/dev08_humo_node_amqp_replay/data/humo_historico.csv"
        SMOKE = list(csv.DictReader(open(p)))
    idx = ((t.hour * 60 + t.minute) // 2) % len(SMOKE)
    r = SMOKE[idx]
    return {"smokeObscuration": float(r["smokeObscuration"]), "ceilingTemp": float(r["ceilingTemp"]),
            "smokeAlarm": r["smokeAlarm"] == "1", "sirenSilenced": False, "replayRow": idx}


def open_meteo(days):
    start = min(days) - timedelta(days=1)
    past = (datetime.now(TZ).date() - start).days + 1
    w = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": LAT, "longitude": LON, "timezone": "UTC", "past_days": min(past, 92),
        "forecast_days": 1, "wind_speed_unit": "ms",
        "hourly": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,precipitation,cloud_cover"},
        timeout=30).json()["hourly"]
    a = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
        "latitude": LAT, "longitude": LON, "timezone": "UTC", "past_days": min(past, 92),
        "forecast_days": 1, "hourly": "pm2_5,pm10,us_aqi"}, timeout=30).json()["hourly"]
    weather, air = [], []
    for k, ts in enumerate(w["time"]):
        t = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        if t.astimezone(TZ).date() not in days or w["temperature_2m"][k] is None:
            continue
        tc, hr = w["temperature_2m"][k], w["relative_humidity_2m"][k]
        dp = dew_point(tc, hr)
        weather.append((t, {"tempOutdoor": tc, "humidity": hr, "dewPoint": dp,
                            "pressure": w["pressure_msl"][k], "windSpeed": w["wind_speed_10m"][k],
                            "rain1h": w["precipitation"][k], "cloudCover": w["cloud_cover"][k],
                            "freeCoolingAvailable": tc < 18 and dp < 15, "sourceAgeMin": 0.0}))
    for k, ts in enumerate(a["time"]):
        t = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        if t.astimezone(TZ).date() not in days or a["pm2_5"][k] is None:
            continue
        air.append((t, {"pm25": a["pm2_5"][k], "pm10": a["pm10"][k], "aqi": a["us_aqi"][k],
                        "sourceAgeMin": 0.0}))
    return weather, air


def series(days, fn):
    out = []
    for d in days:
        t = datetime(d.year, d.month, d.day, tzinfo=TZ)
        # huecos deliberados de 40 min al día (pausas documentadas del replay)
        gap_start = t + timedelta(hours=random.choice([3, 11, 19]))
        while t.date() == d:
            if not (gap_start <= t < gap_start + timedelta(minutes=40)):
                out.append((t.astimezone(timezone.utc), fn(t)))
            t += STEP
    return out


def send_all(device_id, rows, log):
    """Envío por HTTPS REST (sin sesión persistente): no desconecta al mismo
    dispositivo si está transmitiendo en vivo por MQTT/AMQP en paralelo."""
    from concurrent.futures import ThreadPoolExecutor
    key = get_device_key(device_id)
    hub = dps_register_rest(require_env("IOTC_ID_SCOPE"), device_id, key, MODELS[device_id], log)
    url = f"https://{hub}/devices/{device_id}/messages/events?api-version={HTTP_API}"
    sess = requests.Session()
    state = {"tok": None, "exp": 0}

    def token():
        if time.time() > state["exp"] - 120:
            state["tok"] = generate_sas(f"{hub}/devices/{device_id}", key, 3600)
            state["exp"] = time.time() + 3600
        return state["tok"]

    def post(item):
        t, payload = item
        body = json.dumps(dict(payload, replay=True)).encode("utf-8")
        hdr = {"Authorization": token(), "Content-Type": "application/json",
               "iothub-contenttype": "application/json", "iothub-contentencoding": "utf-8",
               "iothub-app-iothub-creation-time-utc": t.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        for _ in range(4):
            r = sess.post(url, data=body, headers=hdr, timeout=30)
            if r.status_code == 204:
                return True
            time.sleep(2)
        log.error("%s HTTP %s %s", device_id, r.status_code, r.text[:150])
        return False

    token()
    ok = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for n, res in enumerate(ex.map(post, rows), 1):
            ok += bool(res)
            if n % 200 == 0:
                log.info("%s: %d/%d", device_id, n, len(rows))
    log.info("%s: %d/%d mensajes históricos enviados (HTTPS)", device_id, ok, len(rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", nargs=4, required=True)
    ap.add_argument("--solo", nargs="*", help="limitar a estos device IDs")
    a = ap.parse_args()
    load_dotenv()
    log = setup_logging("backfill")
    random.seed(20260928)
    days = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in a.dias)
    if any((b - a_).days == 1 for a_, b in zip(days, days[1:])):
        raise SystemExit("Las 4 fechas deben ser NO consecutivas")
    weather, air = open_meteo(set(days))
    plan = {"dc-weather-owm": weather, "dc-airq-api": air,
            "dc-rack-a-py": series(days, rack_a), "dc-aisle-cold-pyws": series(days, aisle),
            "dc-pdu-rest": series(days, pdu), "dc-leak-paho": series(days, leak),
            "dc-smoke-replay": series(days, smoke)}
    for dev, rows in plan.items():
        if a.solo and dev not in a.solo:
            continue
        send_all(dev, rows, log)


if __name__ == "__main__":
    main()
