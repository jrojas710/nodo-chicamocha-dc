# Nodo Chicamocha DC — Parcial 1 IoT Central (UNAB 2026-II)

Autor: **Juan Rojas Guerrero** · Escenario **5.2 Centro de datos** · Bucaramanga

Flota de 10 dispositivos con 10 orígenes de envío distintos hacia Azure IoT Central.

| # | ID en Central | Origen | Protocolo | Intervalo |
|---|---|---|---|---|
| 01 | dc-rack-a-py | Python SDK (**en vivo, portátil 1**) | MQTT 8883 | 15 s |
| 02 | dc-rack-b-wokwi | Wokwi ESP32 #1 (**en vivo, portátil 2**) | MQTT 8883 | 30 s |
| 03 | dc-rack-c-sim | Digital Twin / simulador nativo | interno | plataforma |
| 04 | dc-aisle-cold-pyws | Python SDK #2 | MQTT-WS 443 | 60 s |
| 05 | dc-weather-owm | Feed meteorológico (≈ Atlas Weather) | MQTT 8883 | 5 min |
| 06 | dc-airq-api | API pública de calidad de aire | MQTT 8883 | 15 min |
| 07 | dc-leak-paho | Cliente MQTT explícito (paho) | MQTT 8883 | evento + 5 min |
| 08 | dc-smoke-replay | Replay CSV (Node.js) | AMQPS 5671 | 120 s |
| 09 | dc-pdu-rest | Puente HTTP/REST | HTTPS 443 | 5 min |
| 10 | dc-door-wokwi | Wokwi ESP32 #2 | MQTT 8883 | evento + 10 min |

## Decisiones clave
- **Fuente única de verdad:** `docs/catalogo.py`. De ahí salen las plantillas DTDL, las tablas del PDF y los umbrales del análisis.
- **Provisionamiento:** DPS con clave simétrica derivada de la clave del grupo SAS y payload `{"modelId": ...}`, para que Central asocie la plantilla sola.
- **Desconexión controlada:** comando `simulateOutage(segundos)` en DEV-01, 02, 04, 05 y 06.
- **Doble marca de tiempo en APIs:** `lastSourceTimestamp` y `sourceAgeMin` (fuente) frente a la hora de ingestión del mensaje.
- **Sin secretos en el repo:** `.env` y `secrets.h` están en `.gitignore`.

## Puesta en marcha
```bash
pip install -r requirements.txt
cp .env.example .env              # ID scope + clave de grupo de IoT Central
python templates/gen_dtdl.py      # (ya generadas) importar templates/*.json en Central
python devices/dev01_rack_a_python_mqtt/rack_a.py
python tools/provision.py dc-rack-b-wokwi "dtmi:l0oxnytlx:nvfo9igr;1"   # -> secrets.h en Wokwi
cd devices/dev08_humo_node_amqp_replay && npm install && npm start
```
Wokwi: crear un proyecto ESP32, pegar `sketch.ino` y `diagram.json`, añadir `libraries.txt` y un archivo `secrets.h`.

## Cerrar el documento con datos reales
1. Exportar desde Data Explorer los 4 días no continuos a `datos_4dias/` (CSV).
2. `python tools/analisis_4dias.py datos_4dias/*.csv --dias D1 D2 D3 D4`
3. Guardar capturas en `evidencias/` con los nombres de `evidencias/README.md`.
4. `python docs/build_pdf.py` → `docs/Parcial1_NodoChicamochaDC_JuanRojas.pdf`

Las secciones sin evidencia aparecen como **PENDIENTE** en lugar de mostrar datos inventados.
