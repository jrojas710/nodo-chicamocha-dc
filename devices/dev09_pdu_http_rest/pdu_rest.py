#!/usr/bin/env python3
"""
DEV-09 · PDU / energía de fila · Origen: puente HTTP/REST (HTTPS 443, sin MQTT,
sin SDK). Emula un gateway que lee un medidor trifásico por Modbus RTU y publica
por el endpoint REST de IoT Hub:
    POST https://{hub}/devices/{id}/messages/events?api-version=2020-03-13
Provisionado por DPS REST (payload modelId). HTTP no mantiene sesión: en IoT Central
el estado de conexión de este dispositivo NO pasa a "Connected" como en MQTT; esta es
una limitación documentada del protocolo (la telemetría sí llega).

Medidor de referencia (datasheet): Eastron SDM630-Modbus V2 (clase 1, IEC 62053-21).
Intervalo: 300 s. `energyKwh` es la energía del intervalo -> su SUMATORIA diaria = kWh/día.
Versión: 1.0.0
"""
import json
import random
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import (HTTP_API, clamp, diurnal, dps_register_rest, generate_sas,  # noqa: E402
                         get_device_key, load_dotenv, local_hour, require_env, setup_logging)

DEVICE_ID = "dc-pdu-rest"
MODEL_ID = "dtmi:f9elawiv:mtvnrf8v;1"
INTERVAL_S = 300
V_LN_NOM, V_MIN, V_MAX = 127.0, 114.0, 140.0           # red 220/127 V trifásica (Colombia)
I_BASE, I_AMP, I_MIN, I_MAX, I_OFFSET = 16.0, 4.0, 2.0, 32.0, 0.0   # A por fase (breaker 32 A)
PF_BASE, PF_MIN, PF_MAX = 0.95, 0.80, 1.00
BREAKER_TRIP_PROB = 0.002


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    scope = require_env("IOTC_ID_SCOPE")
    key = get_device_key(DEVICE_ID)
    hub = dps_register_rest(scope, DEVICE_ID, key, MODEL_ID, log)
    url = f"https://{hub}/devices/{DEVICE_ID}/messages/events?api-version={HTTP_API}"
    total_kwh, breaker_closed, sent = 0.0, True, 0
    log.info("PDU | origen puente HTTP/REST | intervalo %d s -> %s", INTERVAL_S, hub)

    while True:
        t0 = time.time()
        try:
            if breaker_closed and random.random() < BREAKER_TRIP_PROB:
                breaker_closed = False
                log.warning("Evento: breaker de la PDU abierto")
            elif not breaker_closed and random.random() < 0.5:
                breaker_closed = True
            i = clamp(diurnal(local_hour(), I_BASE, I_AMP) + random.gauss(0, 0.6) + I_OFFSET,
                      I_MIN, I_MAX) if breaker_closed else 0.0
            v = clamp(V_LN_NOM + random.gauss(0, 1.5), V_MIN, V_MAX)
            pf = clamp(PF_BASE + random.gauss(0, 0.015), PF_MIN, PF_MAX)
            kw = 3 * v * i * pf / 1000.0                        # potencia activa trifásica
            e_int = kw * INTERVAL_S / 3600.0
            total_kwh += e_int
            payload = {"voltageV": round(v, 1), "currentA": round(i, 2), "powerFactor": round(pf, 3),
                       "activePowerKw": round(kw, 3), "energyKwh": round(e_int, 4),
                       "energyTotalKwh": round(total_kwh, 3), "breakerClosed": breaker_closed,
                       "loadPercent": round(100 * i / I_MAX, 1)}
            headers = {"Authorization": generate_sas(f"{hub}/devices/{DEVICE_ID}", key, 3600),
                       "Content-Type": "application/json",
                       "iothub-contenttype": "application/json",
                       "iothub-contentencoding": "utf-8"}
            r = requests.post(url, data=json.dumps(payload).encode("utf-8"),
                              headers=headers, timeout=20)
            if r.status_code == 204:
                sent += 1
                log.info("HTTP 204 TX #%d %s", sent, payload)
            else:
                log.error("HTTP %s %s", r.status_code, r.text[:200])
        except requests.RequestException as e:
            log.error("Fallo de red (%s): hueco en la serie; se reintenta en el próximo ciclo", e)
        except KeyboardInterrupt:
            break
        time.sleep(max(1.0, INTERVAL_S - (time.time() - t0)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Detenido por el operador")
