#!/usr/bin/env python3
"""
DEV-01 · Rack A · Origen: Python + azure-iot-device (DPS + MQTT 8883)
Nodo Chicamocha DC — Parcial 1 IoT Central (UNAB 2026-II) — Juan Rojas Guerrero

Nodo EN VIVO #1 de la sustentación (portátil 1).
Sensores de referencia (datasheet):
  * Sensirion SHT45  -> tempIntake (°C) y humidity (%HR)   ±0.1 °C / ±1.0 %HR
  * Maxim DS18B20    -> tempExhaust (°C)                    ±0.5 °C
Intervalo de muestreo: 15 s (escribible desde Central: sampleIntervalS).

Comandos : setFanBoost(bool), simulateOutage(int s)
Writable : sampleIntervalS, intakeAlarmC
Uso      : python rack_a.py            (lee IOTC_ID_SCOPE e IOTC_GROUP_KEY del entorno/.env)
Versión  : 1.0.0
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import clamp, diurnal, load_dotenv, local_hour, setup_logging  # noqa: E402
from sdk_device import SdkDevice  # noqa: E402

DEVICE_ID = "dc-rack-a-py"
MODEL_ID = "dtmi:l0oxnytlx:nvfo9igr;1"
INTERVAL_S = 15

# Parámetros del código (deben coincidir con la tabla de parámetros del documento)
INTAKE_BASE, INTAKE_AMP, INTAKE_MIN, INTAKE_MAX, INTAKE_OFFSET = 22.5, 1.8, 18.0, 30.0, 0.0
DELTA_T_MIN, DELTA_T_MAX = 10.0, 14.0          # salto térmico servidor (exhaust - intake)
EXHAUST_MIN, EXHAUST_MAX, EXHAUST_OFFSET = 26.0, 46.0, -0.3
HR_BASE, HR_AMP, HR_MIN, HR_MAX, HR_OFFSET = 45.0, 5.0, 30.0, 58.0, 0.0
FAN_BOOST_COOLING = 1.5                         # °C que baja la entrada con boost

state = {"fanBoost": False, "intakeAlarmC": 27.0}


def read_sensors() -> dict:
    h = local_hour()
    intake = diurnal(h, INTAKE_BASE, INTAKE_AMP) + random.gauss(0, 0.15) + INTAKE_OFFSET
    if state["fanBoost"]:
        intake -= FAN_BOOST_COOLING
    intake = round(clamp(intake, INTAKE_MIN, INTAKE_MAX), 2)
    load = diurnal(h, (DELTA_T_MIN + DELTA_T_MAX) / 2, (DELTA_T_MAX - DELTA_T_MIN) / 2)
    exhaust = round(clamp(intake + load + random.gauss(0, 0.3) + EXHAUST_OFFSET,
                          EXHAUST_MIN, EXHAUST_MAX), 2)
    hr = round(clamp(diurnal(h, HR_BASE, HR_AMP, peak_hour=5) + random.gauss(0, 0.5)
                     + HR_OFFSET, HR_MIN, HR_MAX), 1)
    return {"tempIntake": intake, "tempExhaust": exhaust, "humidity": hr,
            "deltaT": round(exhaust - intake, 2),
            "overTemp": intake > state["intakeAlarmC"]}


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    dev = SdkDevice(DEVICE_ID, MODEL_ID, log, websockets=False, sample_interval_s=INTERVAL_S)

    def cmd_fan_boost(payload):
        on = bool(payload if not isinstance(payload, dict) else payload.get("on", True))
        state["fanBoost"] = on
        dev.report({"fanBoostState": on})
        return 200, {"fanBoost": on}

    def set_alarm(value):
        state["intakeAlarmC"] = clamp(float(value), 18.0, 35.0)
        log.info("Umbral local intakeAlarmC -> %.1f °C", state["intakeAlarmC"])

    dev.commands["setFanBoost"] = cmd_fan_boost
    dev.writables["intakeAlarmC"] = set_alarm
    log.info("Rack A | origen Python SDK MQTT | intervalo %d s", INTERVAL_S)
    dev.run(read_sensors)


if __name__ == "__main__":
    main()
