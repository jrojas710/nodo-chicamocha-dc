#!/usr/bin/env python3
"""
DEV-06 · Calidad de aire de admisión (free-cooling) · Origen: API pública de
calidad de aire — Open-Meteo Air Quality API (modelo CAMS de Copernicus), dominio
distinto del feed meteorológico de DEV-05 (otro servicio, otro dataset, otro endpoint).

Justificación operativa: el economizador de free-cooling introduce aire exterior a la
sala; si PM2.5 sube, se cierran los dampers y se revisan filtros MERV-13.
Sensor de referencia para anclaje de datasheet: Plantower PMS5003.
Intervalo de reenvío: 900 s (la fuente es horaria).  Versión: 1.0.0
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import clamp, load_dotenv, setup_logging  # noqa: E402
from sdk_device import SdkDevice  # noqa: E402

DEVICE_ID = "dc-airq-api"
MODEL_ID = "dtmi:yzsvlqec:virbcjtb;1"
INTERVAL_S = 900
LAT = float(os.getenv("SITE_LAT", "7.1193"))
LON = float(os.getenv("SITE_LON", "-73.1227"))
URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

VALID = {"pm25": (0, 500), "pm10": (0, 600), "aqi": (0, 500)}


def fetch() -> tuple[dict, float]:
    r = requests.get(URL, params={"latitude": LAT, "longitude": LON, "timezone": "UTC",
                                  "current": "pm2_5,pm10,us_aqi"}, timeout=20)
    r.raise_for_status()
    c = r.json()["current"]
    data = {"pm25": c.get("pm2_5"), "pm10": c.get("pm10"), "aqi": c.get("us_aqi")}
    ts = datetime.fromisoformat(c["time"]).replace(tzinfo=timezone.utc).timestamp()
    return data, ts


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    dev = SdkDevice(DEVICE_ID, MODEL_ID, log, sample_interval_s=INTERVAL_S)
    dev.origin_label = lambda: "api-bridge-airquality (Open-Meteo CAMS)"

    def sample() -> dict:
        data, src_ts = fetch()
        out = {}
        for k, (lo, hi) in VALID.items():
            if data[k] is not None:
                out[k] = round(clamp(float(data[k]), lo, hi), 1)
        out["sourceAgeMin"] = round((time.time() - src_ts) / 60.0, 1)
        dev.report({"lastSourceTimestamp":
                    datetime.fromtimestamp(src_ts, timezone.utc).isoformat(timespec="seconds"),
                    "provider": "Open-Meteo Air Quality (CAMS)"})
        return out

    log.info("Aire de admisión | origen API pública | intervalo %d s", INTERVAL_S)
    dev.run(sample)


if __name__ == "__main__":
    main()
