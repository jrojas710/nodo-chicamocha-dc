#!/usr/bin/env python3
"""
DEV-07 · Detección de agua bajo piso técnico · Origen: cliente MQTT EXPLÍCITO
(paho-mqtt 2.x, sin SDK de Azure). Se implementa a mano el protocolo MQTT de IoT Hub:
  * DPS por REST (common/iotc_common.dps_register_rest) con payload modelId
  * CONNECT TLS 1.2 :8883, username '{hub}/{deviceId}/?api-version=...&model-id=...'
  * password = token SAS del dispositivo (renovado antes de expirar)
  * PUBLISH devices/{id}/messages/events/$.ct=application%2Fjson&$.ce=utf-8
  * SUBSCRIBE $iothub/methods/POST/#  -> comandos resetLeakLatch / injectLeakTest

Modo de envío: POR EVENTO (cambio de estado de fuga) + LATIDO cada 300 s.
Sensores de referencia: cable detector de fugas por conductividad con controlador
(tipo RLE SeaHawk / LD310) + Sensirion SHT31 (humedad de piso).
Versión: 1.0.0
"""
import json
import random
import ssl
import sys
import threading
import time
import urllib.parse
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from iotc_common import (HUB_API, clamp, dps_register_rest, generate_sas,  # noqa: E402
                         get_device_key, load_dotenv, require_env, setup_logging, utc_now_iso)

DEVICE_ID = "dc-leak-paho"
MODEL_ID = "dtmi:h45esikou:rupkcvyp;1"
HEARTBEAT_S = 300
POLL_S = 5                    # lectura local del cable (no se envía salvo cambio)
SAS_TTL_S = 3600
HR_BASE, HR_MIN, HR_MAX, HR_OFFSET = 48.0, 30.0, 95.0, 0.0
LEAK_PROB_PER_POLL = 0.00015  # ~1 evento espontáneo cada ~9 h de ejecución

state = {"leak": False, "latched": False, "zone": 0, "floorHR": HR_BASE, "events": 0}


def main() -> None:
    load_dotenv()
    log = setup_logging(DEVICE_ID)
    scope = require_env("IOTC_ID_SCOPE")
    key = get_device_key(DEVICE_ID)
    hub = dps_register_rest(scope, DEVICE_ID, key, MODEL_ID, log)

    topic_tx = f"devices/{DEVICE_ID}/messages/events/$.ct=application%2Fjson&$.ce=utf-8"
    username = (f"{hub}/{DEVICE_ID}/?api-version={HUB_API}"
                f"&model-id={urllib.parse.quote(MODEL_ID, safe='')}")
    connected = threading.Event()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID,
                         protocol=mqtt.MQTTv311)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.reconnect_delay_set(min_delay=2, max_delay=60)

    def refresh_password():
        client.username_pw_set(username, generate_sas(f"{hub}/devices/{DEVICE_ID}", key, SAS_TTL_S))

    def on_connect(c, _u, _f, rc, _p):
        if rc == 0:
            log.info("Connected (paho) -> %s:8883", hub)
            c.subscribe("$iothub/methods/POST/#", qos=0)
            connected.set()
        else:
            log.error("CONNACK rechazado: %s", rc)

    def on_disconnect(_c, _u, _f, rc, _p):
        connected.clear()
        log.warning("Disconnected (rc=%s); paho reintentará con backoff", rc)
        refresh_password()   # por si el SAS expiró

    def publish(reason: str):
        payload = {"leakDetected": state["leak"], "leakZone": state["zone"],
                   "floorHumidity": round(state["floorHR"], 1), "eventReason": reason}
        info = client.publish(topic_tx, json.dumps(payload), qos=1)
        log.info("TX (%s) mid=%s %s", reason, info.mid, payload)

    def on_message(c, _u, msg):
        # $iothub/methods/POST/{nombre}/?$rid={rid}
        parts = msg.topic.split("/")
        name, rid = parts[3], msg.topic.split("$rid=")[-1]
        log.info("Comando %s rid=%s payload=%s", name, rid, msg.payload[:200])
        status, body = 200, {}
        if name == "resetLeakLatch":
            if state["leak"]:
                status, body = 409, {"error": "la fuga sigue activa; no se puede rearmar"}
            else:
                state["latched"] = False
                body = {"latched": False, "at": utc_now_iso()}
        elif name == "injectLeakTest":      # prueba funcional del lazo (demo de Rule)
            state["leak"], state["latched"], state["zone"] = True, True, 2
            threading.Timer(90, lambda: state.update(leak=False)).start()
            body = {"testLeakSeconds": 90}
        else:
            status, body = 404, {"error": "comando no implementado"}
        c.publish(f"$iothub/methods/res/{status}/?$rid={rid}", json.dumps(body))
        publish(f"cmd:{name}")

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    refresh_password()
    log.info("Connecting (paho MQTT explícito) | intervalo: evento + latido %d s", HEARTBEAT_S)
    client.connect(hub, 8883, keepalive=120)
    client.loop_start()

    last_hb, last_sas = 0.0, time.time()
    try:
        while True:
            # Lectura local del cable + humedad de piso
            prev = state["leak"]
            if not state["leak"] and random.random() < LEAK_PROB_PER_POLL:
                state["leak"], state["latched"] = True, True
                state["zone"] = random.choice([1, 2, 3])   # 1=Rack A, 2=Rack B, 3=Rack C/CRAC
                threading.Timer(random.uniform(120, 600), lambda: state.update(leak=False)).start()
            target = 88.0 if state["leak"] else HR_BASE
            state["floorHR"] = clamp(state["floorHR"] + (target - state["floorHR"]) * 0.2
                                     + random.gauss(0, 0.3) + HR_OFFSET, HR_MIN, HR_MAX)
            if not state["leak"] and not state["latched"]:
                state["zone"] = 0
            if connected.is_set():
                if state["leak"] != prev:
                    publish("event:leak_on" if state["leak"] else "event:leak_off")
                if time.time() - last_hb >= HEARTBEAT_S:
                    publish("heartbeat")
                    last_hb = time.time()
            if time.time() - last_sas > SAS_TTL_S * 0.8:   # renovación proactiva
                refresh_password()
                client.reconnect()
                last_sas = time.time()
            time.sleep(POLL_S)
    except KeyboardInterrupt:
        log.warning("Detenido por el operador -> DISCONNECT limpio")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
