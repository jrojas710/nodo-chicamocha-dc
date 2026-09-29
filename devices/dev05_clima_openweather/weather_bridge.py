#!/usr/bin/env python3
"""
DEV-05 · Clima exterior para free-cooling · Origen: feed meteorológico
(equivalente a Atlas Weather): OpenWeather Current Weather API 2.5.
Si no hay OPENWEATHER_API_KEY, usa Open-Meteo Forecast como respaldo (sin clave).

Ubicación: Bucaramanga (7.119 N, -73.123 W) — configurable por entorno.
Estación de referencia para el anclaje de datasheet: Davis Vantage Pro2.
Intervalo de reenvío: 300 s (la fuente se actualiza cada ~10–15 min).

Se muestran DOS marcas de tiempo:
  * tiempo de la fuente  -> propiedad `lastSourceTimestamp` + telemetría `sourceAgeMin`
  * tiempo de ingestión  -> marca de tiempo del mensaje en IoT Central (enqueued)
Versión: 1.0.0
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import clamp, dew_point, load_dotenv, setup_logging  # noqa: E402
from sdk_device import SdkDevice  # noqa: E402

DEVICE_ID = "dc-weather-owm"
MODEL_ID = "dtmi:mktff6a:qgkhn7v7;1"
INTERVAL_S = 300
LAT = float(os.getenv("SITE_LAT", "7.1193"))
LON = float(os.getenv("SITE_LON", "-73.1227"))

# Condición de free-cooling (economizador aire-aire, ASHRAE A1 intake 18–27 °C)
FREE_COOLING_MAX_T = 18.0      # °C exterior
FREE_COOLING_MAX_DP = 15.0     # °C punto de rocío máximo (ASHRAE)

# Límites de validación (código): descarta datos fuera de rango físico
VALID = {"tempOutdoor": (-10, 50), "humidity": (0, 100), "pressure": (850, 1100),
         "windSpeed": (0, 60), "rain1h": (0, 150), "cloudCover": (0, 100)}


def from_openweather(key: str) -> tuple[dict, float, str]:
    r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                     params={"lat": LAT, "lon": LON, "appid": key, "units": "metric"},
                     timeout=20)
    r.raise_for_status()
    j = r.json()
    data = {"tempOutdoor": j["main"]["temp"], "humidity": j["main"]["humidity"],
            "pressure": j["main"]["pressure"], "windSpeed": j.get("wind", {}).get("speed", 0.0),
            "rain1h": j.get("rain", {}).get("1h", 0.0), "cloudCover": j.get("clouds", {}).get("all", 0)}
    return data, float(j["dt"]), "OpenWeather 2.5 /weather"


def from_openmeteo() -> tuple[dict, float, str]:
    r = requests.get("https://api.open-meteo.com/v1/forecast",
                     params={"latitude": LAT, "longitude": LON, "timezone": "UTC",
                             "current": "temperature_2m,relative_humidity_2m,pressure_msl,"
                                        "wind_speed_10m,precipitation,cloud_cover",
                             "wind_speed_unit": "ms"}, timeout=20)
    r.raise_for_status()
    c = r.json()["current"]
    data = {"tempOutdoor": c["temperature_2m"], "humidity": c["relative_humidity_2m"],
            "pressure": c.get("pressure_msl", 1013), "windSpeed": c.get("wind_speed_10m", 0.0),
            "rain1h": c.get("precipitation", 0.0), "cloudCover": c.get("cloud_cover", 0)}
    ts = datetime.fromisoformat(c["time"]).replace(tzinfo=timezone.utc).timestamp()
    return data, ts, "Open-Meteo /v1/forecast (respaldo)"


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    dev = SdkDevice(DEVICE_ID, MODEL_ID, log, sample_interval_s=INTERVAL_S)
    dev.origin_label = lambda: "api-bridge-weather (OpenWeather/Open-Meteo)"
    key = os.getenv("OPENWEATHER_API_KEY")
    last = {"provider": None}

    def sample() -> dict:
        try:
            data, src_ts, provider = from_openweather(key) if key else from_openmeteo()
        except Exception as e:  # noqa: BLE001  (cuota, red): intenta el respaldo
            log.warning("Fuente principal falló (%s); usando respaldo Open-Meteo", e)
            data, src_ts, provider = from_openmeteo()
        for k, (lo, hi) in VALID.items():
            data[k] = round(clamp(float(data[k]), lo, hi), 2)
        dp = dew_point(data["tempOutdoor"], data["humidity"])
        data["dewPoint"] = dp
        data["freeCoolingAvailable"] = (data["tempOutdoor"] < FREE_COOLING_MAX_T
                                        and dp < FREE_COOLING_MAX_DP)
        data["sourceAgeMin"] = round((time.time() - src_ts) / 60.0, 1)
        src_iso = datetime.fromtimestamp(src_ts, timezone.utc).isoformat(timespec="seconds")
        dev.report({"lastSourceTimestamp": src_iso, "provider": provider})
        if provider != last["provider"]:
            log.info("Proveedor activo: %s", provider)
            last["provider"] = provider
        return data

    log.info("Clima exterior | origen feed meteorológico | intervalo %d s", INTERVAL_S)
    dev.run(sample)


if __name__ == "__main__":
    main()
