"""
iotc_common.py — utilidades compartidas por los orígenes Python de la flota
Nodo Chicamocha DC (Parcial 1 IoT Central · UNAB 2026-II).

Contiene:
  * lectura de credenciales SOLO desde variables de entorno (.env opcional);
  * derivación de la clave de dispositivo a partir de la clave de grupo SAS
    de IoT Central (enrollment group);
  * generación de tokens SAS (IoT Hub / DPS);
  * registro en DPS por REST (usado por los orígenes que NO usan el SDK:
    paho-mqtt crudo y puente HTTP/REST), con caché del hub asignado.

Versión: 1.0.0
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

DPS_HOST = os.getenv("IOTC_DPS_HOST", "global.azure-devices-provisioning.net")
DPS_API = "2021-06-01"
HUB_API = "2021-04-12"
HTTP_API = "2020-03-13"

CACHE_DIR = Path(os.getenv("IOTC_CACHE_DIR", Path.home() / ".nodo_chicamocha"))


# ----------------------------------------------------------------------------
# Entorno y logging
# ----------------------------------------------------------------------------
def load_dotenv(path: str | os.PathLike | None = None) -> None:
    """Carga un archivo .env simple (CLAVE=valor) sin dependencias externas.
    Nunca sobreescribe variables ya definidas en el entorno."""
    candidates = [Path(path)] if path else [Path.cwd() / ".env",
                                            Path(__file__).resolve().parent.parent / ".env"]
    for p in candidates:
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def setup_logging(device_id: str) -> logging.Logger:
    """Log a consola y a archivo logs/<device_id>.log (evidencia de sesión)."""
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-7s | " + device_id + " | %(message)s"
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=fmt,
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(log_dir / f"{device_id}.log", encoding="utf-8")],
    )
    # El SDK de Azure es muy verboso en DEBUG; se deja en WARNING.
    logging.getLogger("azure").setLevel(logging.WARNING)
    return logging.getLogger(device_id)


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"[config] Falta la variable de entorno {name}. "
                         f"Copie .env.example a .env y complétela (no la suba al repo).")
    return val


# ----------------------------------------------------------------------------
# Claves y tokens
# ----------------------------------------------------------------------------
def derive_device_key(group_key_b64: str, device_id: str) -> str:
    """Clave de dispositivo = Base64(HMAC-SHA256(Base64Decode(groupKey), deviceId)).
    Es el mismo cálculo que hace IoT Central en 'Connect' > 'SAS-IoT-Devices'."""
    key = base64.b64decode(group_key_b64)
    sig = hmac.new(key, device_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("utf-8")


def get_device_key(device_id: str) -> str:
    """Prioriza IOTC_DEVICE_KEY_<ID> ; si no existe, deriva desde IOTC_GROUP_KEY."""
    specific = os.getenv("IOTC_DEVICE_KEY_" + device_id.upper().replace("-", "_"))
    if specific:
        return specific
    return derive_device_key(require_env("IOTC_GROUP_KEY"), device_id)


def generate_sas(resource_uri: str, key_b64: str, ttl_s: int = 3600,
                 policy_name: str | None = None) -> str:
    """Token SAS estándar de Azure IoT (HMAC-SHA256 sobre 'uri\nexpiry')."""
    expiry = int(time.time()) + ttl_s
    uri_enc = urllib.parse.quote(resource_uri, safe="")
    to_sign = f"{uri_enc}\n{expiry}".encode("utf-8")
    sig = base64.b64encode(hmac.new(base64.b64decode(key_b64), to_sign,
                                    hashlib.sha256).digest()).decode("utf-8")
    token = f"SharedAccessSignature sr={uri_enc}&sig={urllib.parse.quote(sig, safe='')}&se={expiry}"
    if policy_name:
        token += f"&skn={policy_name}"
    return token


# ----------------------------------------------------------------------------
# DPS por REST (orígenes sin SDK)
# ----------------------------------------------------------------------------
def dps_register_rest(id_scope: str, device_id: str, device_key: str,
                      model_id: str, log: logging.Logger | None = None,
                      use_cache: bool = True) -> str:
    """Registra el dispositivo en el DPS de IoT Central y devuelve el hub asignado.
    El payload {'modelId': ...} hace que Central asocie la plantilla automáticamente."""
    cache_file = CACHE_DIR / f"{device_id}.json"
    if use_cache and cache_file.is_file():
        data = json.loads(cache_file.read_text())
        if data.get("idScope") == id_scope and data.get("hub"):
            if log:
                log.info("DPS (caché): hub asignado %s", data["hub"])
            return data["hub"]

    base = f"https://{DPS_HOST}/{id_scope}/registrations/{device_id}"
    sas = generate_sas(f"{id_scope}/registrations/{device_id}", device_key,
                       ttl_s=600, policy_name="registration")
    headers = {"Authorization": sas, "Content-Type": "application/json; charset=utf-8"}
    body = {"registrationId": device_id, "payload": {"modelId": model_id}}
    r = requests.put(f"{base}/register?api-version={DPS_API}", json=body,
                     headers=headers, timeout=20)
    r.raise_for_status()
    op = r.json()
    op_id = op["operationId"]
    for _ in range(20):
        if op.get("status") == "assigned":
            break
        time.sleep(2)
        op = requests.get(f"{base}/operations/{op_id}?api-version={DPS_API}",
                          headers=headers, timeout=20).json()
    if op.get("status") != "assigned":
        raise RuntimeError(f"DPS no asignó el dispositivo: {op}")
    hub = op["registrationState"]["assignedHub"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"idScope": id_scope, "hub": hub,
                                      "ts": utc_now_iso()}))
    if log:
        log.info("DPS (REST): dispositivo asignado a %s", hub)
    return hub


# ----------------------------------------------------------------------------
# Utilidades de señal
# ----------------------------------------------------------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def diurnal(hour_local: float, base: float, amp: float, peak_hour: float = 15.0) -> float:
    """Perfil sinusoidal diario (carga de TI / clima) con pico a 'peak_hour'."""
    return base + amp * math.cos((hour_local - peak_hour) / 24.0 * 2 * math.pi)


def dew_point(t_c: float, rh: float) -> float:
    """Punto de rocío por la fórmula de Magnus (a=17.62, b=243.12 °C)."""
    a, b = 17.62, 243.12
    rh = clamp(rh, 1.0, 100.0)
    g = math.log(rh / 100.0) + a * t_c / (b + t_c)
    return round(b * g / (a - g), 2)


def local_hour() -> float:
    """Hora local de Bucaramanga (UTC-5, sin horario de verano)."""
    t = time.gmtime(time.time() - 5 * 3600)
    return t.tm_hour + t.tm_min / 60.0
