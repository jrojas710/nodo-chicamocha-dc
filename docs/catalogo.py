"""
catalogo.py — FUENTE ÚNICA DE VERDAD del proyecto Nodo Chicamocha DC.
De aquí salen: las plantillas DTDL (templates/gen_dtdl.py), las tablas del documento
PDF (docs/build_pdf.py) y los umbrales que usa tools/analisis_4dias.py.
Si cambia un parámetro en un script, cámbielo aquí y regenere todo.
"""

PROJECT = {
    "name": "Nodo Chicamocha DC",
    "tagline": "Centro de datos urbano · Bucaramanga, Santander",
    "company": "Chicamocha Data Center S.A.S. (empresa ficticia del caso)",
    "author": "Juan Rojas Guerrero",
    "email": "juankisrojass@gmail.com",
    "course": "IoT + Cloud + Sistemas Distribuidos",
    "university": "Universidad Autónoma de Bucaramanga (UNAB)",
    "exam": "Parcial 1 · 2026-II",
    "scenario": "5.2 Centro de datos",
    "doc_version": "1.0",
    "site": "Bucaramanga (7.119° N, 73.123° O, ~960 m s. n. m.)",
}

# ----------------------------------------------------------------------------
# Plantillas (Device Templates / Digital Twin) — DTDL v2
# tipo: T=telemetría, P=propiedad (solo lectura), W=propiedad escribible, C=comando
# ----------------------------------------------------------------------------
COMMON_PROPS = [
    ("firmwareVersion", "P", "string", None, "Versión del script / firmware"),
    ("sourceOrigin", "P", "string", None, "Origen de envío declarado"),
    ("lastBoot", "P", "dateTime", None, "Arranque del proceso"),
]

TEMPLATES = {
    "RackThermal": {
        "model": "dtmi:chicamochadc:RackThermal;1",
        "display": "Rack térmico (A/B/C)",
        "items": [
            ("tempIntake", "T", "double", ("Temperature", "degreeCelsius"), "Temperatura de entrada (frontal)"),
            ("tempExhaust", "T", "double", ("Temperature", "degreeCelsius"), "Temperatura de salida (posterior)"),
            ("humidity", "T", "double", ("RelativeHumidity", "percent"), "Humedad relativa en entrada"),
            ("deltaT", "T", "double", ("Temperature", "degreeCelsius"), "Salto térmico del rack"),
            ("overTemp", "T", "boolean", None, "Sobretemperatura local"),
            ("sampleIntervalS", "W", "integer", None, "Intervalo de muestreo (s)"),
            ("intakeAlarmC", "W", "double", ("Temperature", "degreeCelsius"), "Umbral local de sobretemperatura"),
            ("fanBoostState", "P", "boolean", None, "Estado del refuerzo de ventilación"),
            ("setFanBoost", "C", "boolean", None, "Activar / desactivar refuerzo de ventilación"),
            ("simulateOutage", "C", "integer", None, "Desconexión controlada N segundos"),
        ],
    },
    "ColdAisle": {
        "model": "dtmi:chicamochadc:ColdAisle;1",
        "display": "Pasillo frío / contención",
        "items": [
            ("tempAisle", "T", "double", ("Temperature", "degreeCelsius"), "Temperatura de pasillo frío"),
            ("humidity", "T", "double", ("RelativeHumidity", "percent"), "Humedad relativa"),
            ("diffPressure", "T", "double", ("Pressure", "pascal"), "Presión diferencial frío-caliente"),
            ("dewPoint", "T", "double", ("Temperature", "degreeCelsius"), "Punto de rocío"),
            ("sampleIntervalS", "W", "integer", None, "Intervalo de muestreo (s)"),
            ("simulateOutage", "C", "integer", None, "Desconexión controlada N segundos"),
        ],
    },
    "OutdoorWeather": {
        "model": "dtmi:chicamochadc:OutdoorWeather;1",
        "display": "Clima exterior (free-cooling)",
        "items": [
            ("tempOutdoor", "T", "double", ("Temperature", "degreeCelsius"), "Temperatura exterior"),
            ("humidity", "T", "double", ("RelativeHumidity", "percent"), "Humedad relativa exterior"),
            ("dewPoint", "T", "double", ("Temperature", "degreeCelsius"), "Punto de rocío exterior"),
            ("pressure", "T", "double", None, "Presión a nivel del mar (hPa)"),
            ("windSpeed", "T", "double", ("Velocity", "metrePerSecond"), "Velocidad del viento"),
            ("rain1h", "T", "double", None, "Lluvia última hora (mm)"),
            ("cloudCover", "T", "double", None, "Nubosidad (%)"),
            ("freeCoolingAvailable", "T", "boolean", None, "Condición de free-cooling"),
            ("sourceAgeMin", "T", "double", None, "Edad del dato de la fuente (min)"),
            ("lastSourceTimestamp", "P", "dateTime", None, "Marca de tiempo de la fuente"),
            ("provider", "P", "string", None, "Proveedor del feed"),
            ("sampleIntervalS", "W", "integer", None, "Intervalo de reenvío (s)"),
            ("simulateOutage", "C", "integer", None, "Pausa controlada del puente"),
        ],
    },
    "AirIntakeQuality": {
        "model": "dtmi:chicamochadc:AirIntakeQuality;1",
        "display": "Calidad de aire de admisión",
        "items": [
            ("pm25", "T", "double", None, "PM2.5 (µg/m³)"),
            ("pm10", "T", "double", None, "PM10 (µg/m³)"),
            ("aqi", "T", "double", None, "Índice de calidad de aire (US AQI)"),
            ("sourceAgeMin", "T", "double", None, "Edad del dato de la fuente (min)"),
            ("lastSourceTimestamp", "P", "dateTime", None, "Marca de tiempo de la fuente"),
            ("provider", "P", "string", None, "Proveedor de la API"),
            ("sampleIntervalS", "W", "integer", None, "Intervalo de reenvío (s)"),
            ("simulateOutage", "C", "integer", None, "Pausa controlada del puente"),
        ],
    },
    "WaterLeak": {
        "model": "dtmi:chicamochadc:WaterLeak;1",
        "display": "Detección de agua bajo piso",
        "items": [
            ("leakDetected", "T", "boolean", None, "Fuga detectada"),
            ("leakZone", "T", "integer", None, "Zona del cable (0=ninguna,1=A,2=B,3=C/CRAC)"),
            ("floorHumidity", "T", "double", ("RelativeHumidity", "percent"), "Humedad bajo piso"),
            ("eventReason", "T", "string", None, "Causa del mensaje (evento/latido)"),
            ("resetLeakLatch", "C", None, None, "Rearmar enclavamiento de fuga"),
            ("injectLeakTest", "C", None, None, "Prueba funcional de fuga (90 s)"),
        ],
    },
    "SmokeFire": {
        "model": "dtmi:chicamochadc:SmokeFire;1",
        "display": "Detección de humo / incendio",
        "items": [
            ("smokeObscuration", "T", "double", None, "Oscurecimiento por humo (%/ft)"),
            ("ceilingTemp", "T", "double", ("Temperature", "degreeCelsius"), "Temperatura de techo"),
            ("smokeAlarm", "T", "boolean", None, "Alarma de humo"),
            ("sirenSilenced", "T", "boolean", None, "Sirena silenciada"),
            ("replayRow", "T", "integer", None, "Fila del CSV reproducida"),
            ("replaySource", "P", "string", None, "Archivo fuente del replay"),
            ("silenceAlarm", "C", None, None, "Silenciar sirena 300 s"),
        ],
    },
    "PduEnergy": {
        "model": "dtmi:chicamochadc:PduEnergy;1",
        "display": "PDU / energía de fila",
        "items": [
            ("activePowerKw", "T", "double", ("Power", "kilowatt"), "Potencia activa trifásica"),
            ("currentA", "T", "double", ("Current", "ampere"), "Corriente por fase"),
            ("voltageV", "T", "double", ("Voltage", "volt"), "Tensión fase-neutro"),
            ("powerFactor", "T", "double", None, "Factor de potencia"),
            ("energyKwh", "T", "double", ("Energy", "kilowattHour"), "Energía del intervalo"),
            ("energyTotalKwh", "T", "double", ("Energy", "kilowattHour"), "Energía acumulada"),
            ("loadPercent", "T", "double", None, "Carga del breaker (%)"),
            ("breakerClosed", "T", "boolean", None, "Breaker cerrado"),
        ],
    },
    "AccessDoor": {
        "model": "dtmi:chicamochadc:AccessDoor;1",
        "display": "Puerta / control de acceso",
        "items": [
            ("doorOpen", "T", "boolean", None, "Puerta abierta"),
            ("doorOpenSeconds", "T", "integer", None, "Tiempo abierta (s)"),
            ("accessGranted", "T", "integer", None, "Accesos concedidos en el intervalo"),
            ("accessDenied", "T", "integer", None, "Accesos rechazados en el intervalo"),
            ("eventReason", "T", "string", None, "Causa del mensaje"),
            ("doorHeldAlarmS", "W", "integer", None, "Umbral de puerta retenida (s)"),
            ("unlockDoor", "C", "integer", None, "Liberar cerradura N segundos"),
        ],
    },
}

# ----------------------------------------------------------------------------
# Catálogo único de 10 dispositivos (una fila = un origen de envío distinto)
# ----------------------------------------------------------------------------
DEVICES = [
    dict(n="01", id="dc-rack-a-py", zona="Rack A (fila 1)", template="RackThermal",
         origen="Python #1 · azure-iot-device", protocolo="DPS + MQTT/TLS 8883",
         intervalo="15 s", intervalo_s=15, corre="Portátil 1 (EN VIVO)",
         variables="tempIntake, tempExhaust, humidity, deltaT",
         datasheet="Sensirion SHT45; Analog Devices (Maxim) DS18B20",
         distinto="SDK oficial de Python, sesión MQTT persistente, comandos y propiedades escribibles.",
         codigo="devices/dev01_rack_a_python_mqtt/rack_a.py"),
    dict(n="02", id="dc-rack-b-wokwi", zona="Rack B (fila 1)", template="RackThermal",
         origen="Wokwi ESP32 #1 (Arduino)", protocolo="MQTT/TLS 8883 (PubSubClient + SAS en el borde)",
         intervalo="30 s", intervalo_s=30, corre="Portátil 2 · navegador (EN VIVO)",
         variables="tempIntake, tempExhaust, humidity, deltaT",
         datasheet="Aosong DHT22/AM2302; DS18B20",
         distinto="Firmware C++ en microcontrolador simulado; firma SAS con mbedTLS; actuador (relé) por comando.",
         codigo="devices/dev02_rack_b_wokwi/sketch.ino"),
    dict(n="03", id="dc-rack-c-sim", zona="Rack C (fila 1)", template="RackThermal",
         origen="Digital Twin · simulador nativo", protocolo="Interno de IoT Central",
         intervalo="Fija de la plataforma", intervalo_s=None, corre="IoT Central (nube)",
         variables="tempIntake, tempExhaust, humidity, deltaT",
         datasheet="Mismo modelo que Rack A/B (referencia SHT45 / DS18B20)",
         distinto="Dispositivo simulado creado sobre la plantilla; no hay código del grupo.",
         codigo="devices/dev03_rack_c_simulado/README.md"),
    dict(n="04", id="dc-aisle-cold-pyws", zona="Pasillo frío / contención", template="ColdAisle",
         origen="Python #2 · protocolo distinto", protocolo="DPS + MQTT sobre WebSockets TLS 443",
         intervalo="60 s", intervalo_s=60, corre="VM / portátil (segundo plano)",
         variables="tempAisle, humidity, diffPressure, dewPoint",
         datasheet="Sensirion SHT45; Sensirion SDP810-125Pa",
         distinto="Transporte WebSocket 443 (apto para redes que bloquean 8883); cálculo de punto de rocío en el borde.",
         codigo="devices/dev04_pasillo_python_mqttws/aisle.py"),
    dict(n="05", id="dc-weather-owm", zona="Cubierta / clima exterior", template="OutdoorWeather",
         origen="Feed meteorológico (equivalente Atlas Weather)", protocolo="HTTPS→API OpenWeather · MQTT 8883→Central",
         intervalo="5 min", intervalo_s=300, corre="VM (segundo plano)",
         variables="tempOutdoor, humidity, dewPoint, pressure, windSpeed, rain1h, cloudCover",
         datasheet="Referencia de estación: Davis Vantage Pro2 (ISS 6152)",
         distinto="Datos meteorológicos reales de Bucaramanga; doble marca de tiempo (fuente / ingestión); respaldo Open-Meteo.",
         codigo="devices/dev05_clima_openweather/weather_bridge.py"),
    dict(n="06", id="dc-airq-api", zona="Toma de aire del free-cooling", template="AirIntakeQuality",
         origen="API pública (calidad de aire)", protocolo="HTTPS→Open-Meteo AQ · MQTT 8883→Central",
         intervalo="15 min", intervalo_s=900, corre="VM (segundo plano)",
         variables="pm25, pm10, aqi, sourceAgeMin",
         datasheet="Referencia: Plantower PMS5003",
         distinto="Otro proveedor y otro dominio de datos (calidad de aire, modelo CAMS), fuente horaria.",
         codigo="devices/dev06_aire_openmeteo/airquality_bridge.py"),
    dict(n="07", id="dc-leak-paho", zona="Piso técnico (cable perimetral)", template="WaterLeak",
         origen="Cliente MQTT explícito (paho-mqtt)", protocolo="DPS REST + MQTT/TLS 8883 crudo",
         intervalo="Evento + latido 5 min", intervalo_s=300, corre="VM (segundo plano)",
         variables="leakDetected, leakZone, floorHumidity",
         datasheet="Cable de fuga por conductividad (tipo RLE SeaHawk/LD310); Sensirion SHT31",
         distinto="Sin SDK: tópicos, SAS y respuestas de comando implementados a mano; envío dirigido por evento.",
         codigo="devices/dev07_agua_paho_mqtt/leak_paho.py"),
    dict(n="08", id="dc-smoke-replay", zona="Techo sala / cuarto UPS", template="SmokeFire",
         origen="Replay de CSV histórico (Node.js)", protocolo="DPS + AMQPS 5671",
         intervalo="120 s", intervalo_s=120, corre="VM (segundo plano)",
         variables="smokeObscuration, ceilingTemp, smokeAlarm",
         datasheet="Detector fotoeléctrico listado UL 268; DS18B20 (techo)",
         distinto="Otro lenguaje (JavaScript) y otro protocolo (AMQP); reproduce un perfil de prueba de 24 h.",
         codigo="devices/dev08_humo_node_amqp_replay/replay.js"),
    dict(n="09", id="dc-pdu-rest", zona="PDU de fila 1", template="PduEnergy",
         origen="Puente HTTP/REST (gateway Modbus)", protocolo="DPS REST + HTTPS 443 POST",
         intervalo="5 min", intervalo_s=300, corre="VM (segundo plano)",
         variables="activePowerKw, currentA, voltageV, powerFactor, energyKwh",
         datasheet="Eastron SDM630-Modbus V2",
         distinto="Sin sesión persistente: cada muestra es un POST HTTPS firmado; sin comandos (limitación HTTP).",
         codigo="devices/dev09_pdu_http_rest/pdu_rest.py"),
    dict(n="10", id="dc-door-wokwi", zona="Puerta de sala blanca", template="AccessDoor",
         origen="Wokwi ESP32 #2 (segunda instancia)", protocolo="MQTT/TLS 8883",
         intervalo="Evento + latido 10 min", intervalo_s=600, corre="Navegador (contingencia en vivo)",
         variables="doorOpen, doorOpenSeconds, accessGranted, accessDenied",
         datasheet="Contacto magnético MC-38; lector RFID 13,56 MHz (MFRC522)",
         distinto="Circuito y sketch distintos a DEV-02; entradas digitales dirigidas por evento; comando de cerradura.",
         codigo="devices/dev10_puerta_wokwi/sketch.ino"),
]

# ----------------------------------------------------------------------------
# Tabla de parámetros por variable
# (dev, variable, unidad, rango datasheet, rango operativo, precisión, umbral Rule, código)
# ----------------------------------------------------------------------------
VARS = [
    ("01-03", "tempIntake", "°C", "−40…125 (SHT45) / −40…80 (DHT22)", "18…27 (ASHRAE A1 recom.)", "±0,1 °C / ±0,5 °C", "> 27 aviso · > 32 crítico", "base 22,5 ± 1,8; clamp 18…30; offset 0,0"),
    ("01-03", "tempExhaust", "°C", "−55…125 (DS18B20)", "28…45", "±0,5 °C (−10…85 °C)", "> 45 aviso", "intake + ΔT 10…14; clamp 26…46; offset −0,3"),
    ("01-03", "humidity", "%HR", "0…100 (SHT45 / DHT22)", "20…60", "±1,0 %HR / ±2–5 %HR", "> 60 aviso · < 20 aviso (ESD)", "base 45 ± 5; clamp 30…58; offset 0,0"),
    ("04", "tempAisle", "°C", "−40…125 (SHT45)", "18…27", "±0,1 °C", "> 27 aviso", "base 20,5 ± 1,2; clamp 17…27; offset 0,0"),
    ("04", "diffPressure", "Pa", "−125…+125 (SDP810-125Pa)", "+2…+10", "±3 % de lectura (típ.)", "< 2 aviso (fuga de contención)", "base 4,5 σ0,35; eventos 0,3…1,6; clamp 0…10; offset cero 0,2"),
    ("04", "dewPoint", "°C", "calculado (Magnus)", "−9…15 (ASHRAE)", "≈ ±0,3 °C (propagado)", "> 15 aviso", "Magnus a=17,62 b=243,12"),
    ("05", "tempOutdoor", "°C", "−40…65 (Davis VP2)", "17…32 (Bucaramanga)", "±0,3 °C", "> 30 info (sin free-cooling)", "validación −10…50"),
    ("05", "humidity (ext.)", "%HR", "1…100 (Davis VP2)", "50…95", "±2 %HR (0–90 %)", "—", "validación 0…100"),
    ("05", "windSpeed", "m/s", "0,5…89 (Davis VP2)", "0…8", "±1 m/s o ±5 %", "> 15 aviso (cubierta)", "validación 0…60"),
    ("05", "rain1h", "mm", "0,2 mm/resolución (Davis VP2)", "0…40", "±4 % (típ.)", "> 20 aviso (filtraciones)", "validación 0…150"),
    ("06", "pm25", "µg/m³", "0…500 efectivo (PMS5003)", "5…35", "±10 µg/m³ (0–100)", "> 35,4 aviso (cerrar dampers)", "validación 0…500"),
    ("06", "pm10", "µg/m³", "0…500 efectivo (PMS5003)", "10…60", "±10 µg/m³ (0–100)", "> 154 aviso", "validación 0…600"),
    ("06", "aqi", "—", "0…500 (US EPA)", "0…100", "derivado", "> 100 aviso", "validación 0…500"),
    ("07", "leakDetected", "bool", "contacto seco (cable conductivo)", "false", "binaria", "= true crítico", "prob. 1,5e−4 por sondeo de 5 s"),
    ("07", "floorHumidity", "%HR", "0…100 (SHT31)", "30…70", "±2 %HR", "> 80 aviso", "base 48; clamp 30…95; offset 0,0"),
    ("08", "smokeObscuration", "%/ft", "0,5…4,0 sensibilidad (UL 268)", "0…0,2", "según listado", "> 1,5 pre-alarma", "CSV 720 filas; máx. 3,6"),
    ("08", "ceilingTemp", "°C", "−55…125 (DS18B20)", "20…35", "±0,5 °C", "> 57 crítico (detector térmico)", "CSV 23,4…34,6"),
    ("08", "smokeAlarm", "bool", "salida de alarma del detector", "false", "binaria", "= true crítico", "obscuration ≥ 2,5 %/ft"),
    ("09", "currentA", "A", "0,5…100 (SDM630 directo)", "5…25,6", "±0,5 % (clase 1)", "> 25,6 aviso (80 % de 32 A)", "base 16 ± 4; clamp 2…32; offset 0,0"),
    ("09", "voltageV", "V", "100…289 F-N (SDM630)", "114…140 (127 V ±10 %)", "±0,5 %", "< 114 o > 140 aviso", "127 σ1,5; clamp 114…140"),
    ("09", "powerFactor", "—", "−1…1 (SDM630)", "0,90…1,00", "±1 %", "< 0,90 aviso", "0,95 σ0,015; clamp 0,80…1,00"),
    ("09", "activePowerKw", "kW", "calculado 3·V·I·FP", "3…9", "clase 1", "> 9,5 aviso", "derivado"),
    ("09", "energyKwh", "kWh", "registro de energía (SDM630)", "0,2…0,8 por 5 min", "clase 1", "— (sumatoria diaria)", "kW × 300 s / 3600"),
    ("10", "doorOpen", "bool", "gap ≤ 15–25 mm (MC-38)", "false", "binaria", "—", "slide switch Wokwi"),
    ("10", "doorOpenSeconds", "s", "contador de firmware", "0…60", "1 s", "> 120 aviso (puerta retenida)", "reporte c/30 s si abierta"),
    ("10", "accessDenied", "eventos", "lector 13,56 MHz (MFRC522)", "0…2 por hora", "conteo", "suma > 3 en 5 min aviso", "pulsador rojo"),
]

# ----------------------------------------------------------------------------
# Rules de IoT Central (categorías separadas: térmica, contención, agua, humo, energía, acceso, exterior)
# ----------------------------------------------------------------------------
RULES = [
    ("R01", "Térmica", "Rack · entrada alta", "RackThermal", "tempIntake > 27 (promedio 5 min)", "Aviso", "Correo NOC + webhook"),
    ("R02", "Térmica", "Rack · entrada crítica", "RackThermal", "tempIntake > 32 (sin agregación)", "Crítico", "Correo NOC + Power Automate → setFanBoost"),
    ("R03", "Térmica", "Rack · humedad fuera de rango", "RackThermal", "humidity > 60 o < 20 (promedio 5 min)", "Aviso", "Correo"),
    ("R04", "Contención", "Pérdida de presión diferencial", "ColdAisle", "diffPressure < 2 (promedio 5 min)", "Aviso", "Correo"),
    ("R05", "Contención", "Riesgo de condensación", "ColdAisle", "dewPoint > 15", "Aviso", "Correo"),
    ("R06", "Agua", "Fuga bajo piso", "WaterLeak", "leakDetected = true", "Crítico", "Correo + webhook"),
    ("R07", "Humo", "Pre-alarma de humo", "SmokeFire", "smokeObscuration > 1,5", "Aviso", "Correo"),
    ("R08", "Humo", "Alarma de incendio", "SmokeFire", "smokeAlarm = true o ceilingTemp > 57", "Crítico", "Correo + webhook"),
    ("R09", "Energía", "Sobrecarga de PDU", "PduEnergy", "currentA > 25,6 (promedio 5 min)", "Aviso", "Correo"),
    ("R10", "Energía", "Breaker abierto / FP bajo", "PduEnergy", "breakerClosed = false · powerFactor < 0,9", "Crítico / Aviso", "Correo + webhook"),
    ("R11", "Acceso", "Puerta retenida", "AccessDoor", "doorOpenSeconds > 120", "Aviso", "Correo"),
    ("R12", "Acceso", "Intentos rechazados", "AccessDoor", "suma(accessDenied) > 3 en 5 min", "Aviso", "Correo"),
    ("R13", "Exterior", "Aire exterior contaminado", "AirIntakeQuality", "pm25 > 35,4 o aqi > 100", "Aviso", "Correo (cerrar dampers)"),
    ("R14", "Exterior", "Sin free-cooling por calor", "OutdoorWeather", "tempOutdoor > 30 (promedio 15 min)", "Info", "Correo"),
]

# ----------------------------------------------------------------------------
# Historial de versiones
# ----------------------------------------------------------------------------
VERSIONS = [
    ("0.1", "2026-09-28", "Juan Rojas Guerrero", "Selección del escenario 5.2, catálogo de 10 orígenes y arquitectura."),
    ("0.2", "2026-09-28", "Juan Rojas Guerrero", "Plantillas DTDL v1 (8 interfaces), Rules R01–R14 y tablas de parámetros."),
    ("0.3", "2026-09-28", "Juan Rojas Guerrero", "Códigos de los 10 orígenes v1.0.0, herramienta de análisis de 4 días."),
    ("1.0", "2026-09-28", "Juan Rojas Guerrero", "Expediente completo; secciones de evidencia listas para capturas."),
]

ARTIFACT_VERSIONS = [
    ("Device Templates (8 × DTDL v2)", "1", "templates/*.json — modelId ...;1"),
    ("common/iotc_common.py · sdk_device.py", "1.0.0", "Utilidades DPS/SAS y envoltorio SDK"),
    ("dev01 rack_a.py", "1.0.0", "Python SDK MQTT"),
    ("dev02 sketch.ino (Rack B)", "1.0.0", "Wokwi ESP32 #1"),
    ("dev04 aisle.py", "1.0.0", "Python SDK MQTT-WS"),
    ("dev05 weather_bridge.py", "1.0.0", "OpenWeather / Open-Meteo"),
    ("dev06 airquality_bridge.py", "1.0.0", "Open-Meteo Air Quality"),
    ("dev07 leak_paho.py", "1.0.0", "paho-mqtt crudo"),
    ("dev08 replay.js", "1.0.0", "Node.js AMQP + CSV"),
    ("dev09 pdu_rest.py", "1.0.0", "HTTPS REST"),
    ("dev10 sketch.ino (Puerta)", "1.0.0", "Wokwi ESP32 #2"),
    ("tools/analisis_4dias.py", "1.0.0", "Estadística de los 4 días"),
]
