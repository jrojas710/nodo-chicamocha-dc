#!/usr/bin/env python3
"""
DEV-04 · Pasillo frío / contención · Origen: segundo script Python con OTRO
protocolo: MQTT sobre WebSockets (TLS 443) — atraviesa firewalls/proxy corporativos
que bloquean 8883. DPS también por WebSockets.

Sensores de referencia (datasheet):
  * Sensirion SHT45          -> tempAisle (°C), humidity (%HR)
  * Sensirion SDP810-125Pa   -> diffPressure (Pa) entre pasillo frío y caliente
  * dewPoint (°C) calculado (Magnus) en el borde
Intervalo: 60 s (escribible).  Versión: 1.0.0
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import (clamp, dew_point, diurnal, load_dotenv,  # noqa: E402
                         local_hour, setup_logging)
from sdk_device import SdkDevice  # noqa: E402

DEVICE_ID = "dc-aisle-cold-pyws"
MODEL_ID = "dtmi:r2siy0a3m:l6ditz2k;1"
INTERVAL_S = 60

T_BASE, T_AMP, T_MIN, T_MAX, T_OFFSET = 20.5, 1.2, 17.0, 27.0, 0.0
HR_BASE, HR_AMP, HR_MIN, HR_MAX, HR_OFFSET = 46.0, 4.0, 30.0, 60.0, 0.0
DP_BASE, DP_MIN, DP_MAX, DP_ZERO_OFFSET = 4.5, 0.0, 10.0, 0.2   # Pa
DOOR_OPEN_PROB = 0.04    # prob. de puerta de contención abierta (caída de dP)


def read_sensors() -> dict:
    h = local_hour()
    t = round(clamp(diurnal(h, T_BASE, T_AMP) + random.gauss(0, 0.1) + T_OFFSET, T_MIN, T_MAX), 2)
    hr = round(clamp(diurnal(h, HR_BASE, HR_AMP, 5) + random.gauss(0, 0.4) + HR_OFFSET,
                     HR_MIN, HR_MAX), 1)
    dp = DP_BASE + random.gauss(0, 0.35)
    if random.random() < DOOR_OPEN_PROB:          # evento real: puerta de contención abierta
        dp = random.uniform(0.3, 1.6)
    dp = round(clamp(dp - DP_ZERO_OFFSET, DP_MIN, DP_MAX), 2)
    return {"tempAisle": t, "humidity": hr, "diffPressure": dp, "dewPoint": dew_point(t, hr)}


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    dev = SdkDevice(DEVICE_ID, MODEL_ID, log, websockets=True, sample_interval_s=INTERVAL_S)
    log.info("Pasillo frío | origen Python SDK MQTT-over-WebSockets:443 | intervalo %d s", INTERVAL_S)
    dev.run(read_sensors)


if __name__ == "__main__":
    main()
