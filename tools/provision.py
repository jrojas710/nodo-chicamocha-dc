#!/usr/bin/env python3
"""
provision.py — Registra un dispositivo en el DPS de IoT Central por REST y muestra
el hub asignado y la clave derivada. Se usa para los orígenes que NO hacen DPS por
sí mismos (Wokwi DEV-02 y DEV-10): sus valores se copian a secrets.h.

Uso:
    python tools/provision.py dc-rack-b-wokwi "dtmi:l0oxnytlx:nvfo9igr;1"
    python tools/provision.py dc-door-wokwi  "dtmi:plk6v9d:prxhobho;1"
Requiere IOTC_ID_SCOPE e IOTC_GROUP_KEY en el entorno (.env).  Versión: 1.0.0
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from iotc_common import (dps_register_rest, get_device_key, load_dotenv,  # noqa: E402
                         require_env, setup_logging)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    device_id, model_id = sys.argv[1], sys.argv[2]
    load_dotenv()
    log = setup_logging("provision")
    key = get_device_key(device_id)
    hub = dps_register_rest(require_env("IOTC_ID_SCOPE"), device_id, key, model_id, log,
                            use_cache=False)
    print("\n// ---- pegar en secrets.h ----")
    print(f'#define IOT_HUB_HOST   "{hub}"')
    print(f'#define DEVICE_ID      "{device_id}"')
    print(f'#define DEVICE_KEY_B64 "{key}"')
    print("// No comparta ni suba este bloque al repositorio.")


if __name__ == "__main__":
    main()
