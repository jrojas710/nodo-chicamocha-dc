"""
sdk_device.py — envoltorio del SDK azure-iot-device (v2.x) usado por los orígenes
Python de la flota (dev01, dev04, dev05, dev06).

  * Provisiona por DPS con clave simétrica y payload {"modelId": ...}.
  * Transporte MQTT (8883) o MQTT sobre WebSockets (443) según `websockets`.
  * Registra comandos y propiedades escribibles con ACK según convención
    IoT Plug and Play ({"value", "ac", "ad", "av"}).
  * Implementa el comando `simulateOutage` (desconexión controlada + reconexión),
    que es la evidencia de "hueco en la serie" pedida por el parcial.

Versión: 1.0.0
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable

from azure.iot.device import (IoTHubDeviceClient, Message, MethodResponse,
                              ProvisioningDeviceClient)

from iotc_common import get_device_key, require_env, utc_now_iso

CommandHandler = Callable[[Any], tuple[int, dict]]


class SdkDevice:
    def __init__(self, device_id: str, model_id: str, log: logging.Logger,
                 websockets: bool = False, sample_interval_s: int = 60):
        self.device_id = device_id
        self.model_id = model_id
        self.log = log
        self.websockets = websockets
        self.sample_interval_s = sample_interval_s
        self.id_scope = require_env("IOTC_ID_SCOPE")
        self.device_key = get_device_key(device_id)
        self.client: IoTHubDeviceClient | None = None
        self.hub: str | None = None
        self.commands: dict[str, CommandHandler] = {}
        self.writables: dict[str, Callable[[Any], None]] = {}
        self._outage_until = 0.0
        self._lock = threading.Lock()
        self.sent = 0
        self._outage_active = False
        # Comandos comunes a todos los orígenes SDK
        self.commands["simulateOutage"] = self._cmd_simulate_outage
        self.writables["sampleIntervalS"] = self._set_interval

    # ------------------------------------------------------------------ DPS
    def provision(self) -> str:
        transport = "MQTT-WS:443" if self.websockets else "MQTT:8883"
        self.log.info("Connecting | DPS %s | scope=%s | transporte=%s",
                      self.device_id, self.id_scope, transport)
        prov = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=os.getenv("IOTC_DPS_HOST", "global.azure-devices-provisioning.net"),
            registration_id=self.device_id,
            id_scope=self.id_scope,
            symmetric_key=self.device_key,
            websockets=self.websockets,
        )
        prov.provisioning_payload = {"modelId": self.model_id}
        result = prov.register()
        if result.status != "assigned":
            raise RuntimeError(f"DPS status={result.status}")
        self.hub = result.registration_state.assigned_hub
        self.log.info("DPS asignado -> %s", self.hub)
        return self.hub

    # -------------------------------------------------------------- conexión
    def connect(self) -> None:
        if not self.hub:
            self.provision()
        self.client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=self.device_key,
            hostname=self.hub,
            device_id=self.device_id,
            product_info=self.model_id,       # anuncia el modelo PnP
            websockets=self.websockets,
            connection_retry=True,
        )
        self.client.on_method_request_received = self._on_method
        self.client.on_twin_desired_properties_patch_received = self._on_desired
        self.client.on_connection_state_change = self._on_state
        self.client.connect()
        self.log.info("Connected | hub=%s", self.hub)
        self._sync_initial_twin()

    def disconnect(self) -> None:
        if self.client:
            try:
                self.client.shutdown()
            except Exception as e:  # noqa: BLE001
                self.log.warning("shutdown: %s", e)
            self.client = None
            self.log.info("Disconnected (cliente cerrado)")

    def _on_state(self) -> None:
        if self.client:
            self.log.info("Estado de conexión: %s",
                          "Connected" if self.client.connected else "Disconnected")

    # ------------------------------------------------------------ telemetría
    def send(self, payload: dict) -> bool:
        if time.time() < self._outage_until or not self.client:
            self.log.info("Hueco controlado: muestra NO enviada %s", payload)
            return False
        msg = Message(json.dumps(payload))
        msg.content_encoding = "utf-8"
        msg.content_type = "application/json"
        try:
            self.client.send_message(msg)
            self.sent += 1
            self.log.info("TX #%d %s", self.sent, payload)
            return True
        except Exception as e:  # noqa: BLE001
            self.log.error("Fallo de envío (%s); el SDK reintentará", e)
            return False

    def report(self, props: dict) -> None:
        if self.client:
            self.client.patch_twin_reported_properties(props)
            self.log.info("Reported properties %s", props)

    # --------------------------------------------------------- comandos/props
    def _on_method(self, req) -> None:
        self.log.info("Comando recibido: %s payload=%s", req.name, req.payload)
        handler = self.commands.get(req.name)
        if handler is None:
            status, body = 404, {"error": f"comando {req.name} no implementado"}
        else:
            try:
                status, body = handler(req.payload)
            except Exception as e:  # noqa: BLE001
                status, body = 500, {"error": str(e)}
        self.client.send_method_response(
            MethodResponse.create_from_method_request(req, status, body))
        self.log.info("Respuesta comando %s -> %d %s", req.name, status, body)

    def _on_desired(self, patch: dict) -> None:
        version = patch.get("$version")
        for name, value in patch.items():
            if name.startswith("$"):
                continue
            setter = self.writables.get(name)
            if setter:
                setter(value)
                ack = {"value": value, "ac": 200, "ad": "aplicado", "av": version}
            else:
                ack = {"value": value, "ac": 400, "ad": "propiedad desconocida", "av": version}
            self.report({name: ack})

    def _sync_initial_twin(self) -> None:
        twin = self.client.get_twin()
        desired = twin.get("desired", {})
        for name, setter in self.writables.items():
            if name in desired:
                setter(desired[name])
        self.report({"sampleIntervalS": {"value": self.sample_interval_s, "ac": 200,
                                         "ad": "valor inicial", "av": desired.get("$version", 1)},
                     "firmwareVersion": os.getenv("APP_VERSION", "1.0.0"),
                     "sourceOrigin": self.origin_label(),
                     "lastBoot": utc_now_iso()})

    def origin_label(self) -> str:
        return "python-sdk-mqtt-ws" if self.websockets else "python-sdk-mqtt"

    def _set_interval(self, value: Any) -> None:
        try:
            v = int(value)
            if 5 <= v <= 3600:
                self.sample_interval_s = v
                self.log.info("Intervalo de muestreo -> %d s", v)
        except (TypeError, ValueError):
            pass

    def _cmd_simulate_outage(self, payload) -> tuple[int, dict]:
        """Desconexión controlada: cierra la sesión MQTT N segundos y reconecta.
        En Central el dispositivo pasa a Disconnected y la serie muestra un hueco."""
        seconds = int(payload or 120) if not isinstance(payload, dict) \
            else int(payload.get("seconds", 120))
        seconds = max(30, min(seconds, 1800))
        self._outage_until = time.time() + seconds

        def _worker():
            self._outage_active = True
            time.sleep(1.5)  # deja salir la respuesta del comando
            self.log.warning("=== DESCONEXIÓN CONTROLADA %d s ===", seconds)
            self.disconnect()
            time.sleep(seconds)
            self.log.warning("=== RECONEXIÓN ===")
            try:
                self.connect()
            finally:
                self._outage_active = False

        threading.Thread(target=_worker, daemon=True).start()
        return 200, {"outageSeconds": seconds, "reconnectAt": time.time() + seconds}

    # ----------------------------------------------------------------- bucle
    def run(self, sample_fn: Callable[[], dict]) -> None:
        """Bucle principal con reconexión si la red cae (fallo no controlado)."""
        self.connect()
        try:
            while True:
                t0 = time.time()
                if self.client is not None or time.time() < self._outage_until:
                    try:
                        self.send(sample_fn())
                    except Exception as e:  # noqa: BLE001
                        self.log.error("Error de muestreo: %s", e)
                elif not self._outage_active:
                    try:
                        self.connect()
                    except Exception as e:  # noqa: BLE001
                        self.log.error("Reconexión fallida: %s (reintento)", e)
                time.sleep(max(1.0, self.sample_interval_s - (time.time() - t0)))
        except KeyboardInterrupt:
            self.log.warning("Detenido por el operador (Ctrl+C) -> apagado controlado")
        finally:
            self.disconnect()
