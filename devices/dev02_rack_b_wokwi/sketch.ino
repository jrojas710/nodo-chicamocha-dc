/*
 * DEV-02 · Rack B · Origen: Wokwi ESP32 (Arduino) -> IoT Central (MQTT/TLS 8883)
 * Nodo Chicamocha DC — Parcial 1 IoT Central (UNAB 2026-II) — Juan Rojas Guerrero
 *
 * Nodo EN VIVO #2 de la sustentación (portátil 2, navegador con Wokwi).
 *
 * Sensores (datasheet):
 *   DHT22 / AM2302  -> tempIntake (°C) y humidity (%HR)   ±0.5 °C / ±2–5 %HR
 *   DS18B20         -> tempExhaust (°C)                    ±0.5 °C
 * Actuador: relé + LED "FAN BOOST" (comando setFanBoost)
 * LED rojo: sobretemperatura local (tempIntake > intakeAlarmC, escribible desde Central)
 *
 * Intervalo: 30 s (escribible: sampleIntervalS).
 * Comandos : setFanBoost(bool), simulateOutage(int s)
 *
 * Credenciales: secrets.h (NO se sube; ver secrets.h.example). El hub asignado se
 * obtiene con tools/provision.py (DPS REST con payload modelId), que también imprime
 * la clave derivada del dispositivo.
 * Versión: 1.0.0
 */
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHTesp.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <time.h>
#include "mbedtls/md.h"
#include "mbedtls/base64.h"
#include "secrets.h"      // IOT_HUB_HOST, DEVICE_ID, DEVICE_KEY_B64, AZURE_ROOT_CA (opcional)

#define PIN_DHT      15
#define PIN_ONEWIRE  4
#define PIN_RELAY    26
#define PIN_LED_ALM  2
#define PIN_LED_NET  27

static const char* MODEL_ID  = "dtmi:l0oxnytlx:nvfo9igr;1";
static const char* FW_VER    = "1.0.0";
// Parámetros del código (tabla de parámetros): offsets de calibración y límites
static const float INTAKE_OFFSET = 0.0f, EXHAUST_OFFSET = -0.3f, HR_OFFSET = 0.0f;
static const float T_VALID_MIN = 10.0f, T_VALID_MAX = 50.0f;

WiFiClientSecure tls;
PubSubClient mqtt(tls);
DHTesp dht;
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature ds(&oneWire);

uint32_t sampleIntervalS = 30;
float intakeAlarmC = 27.0f;
bool fanBoost = false;
uint32_t lastTx = 0, outageUntil = 0, sasExpiry = 0, txCount = 0, twinRid = 1;
String sas, username;

// ---------------------------------------------------------------- SAS token
String urlEncode(const String& s) {
  String o; char b[4];
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') o += c;
    else { snprintf(b, sizeof(b), "%%%02X", (uint8_t)c); o += b; }
  }
  return o;
}

String makeSas(uint32_t ttl) {
  sasExpiry = time(nullptr) + ttl;
  String uri = urlEncode(String(IOT_HUB_HOST) + "/devices/" + DEVICE_ID);
  String toSign = uri + "\n" + String(sasExpiry);
  uint8_t key[64]; size_t keyLen = 0;
  mbedtls_base64_decode(key, sizeof(key), &keyLen, (const uint8_t*)DEVICE_KEY_B64, strlen(DEVICE_KEY_B64));
  uint8_t hmac[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&ctx, key, keyLen);
  mbedtls_md_hmac_update(&ctx, (const uint8_t*)toSign.c_str(), toSign.length());
  mbedtls_md_hmac_finish(&ctx, hmac);
  mbedtls_md_free(&ctx);
  uint8_t sig[64]; size_t sigLen = 0;
  mbedtls_base64_encode(sig, sizeof(sig), &sigLen, hmac, 32);
  return "SharedAccessSignature sr=" + uri + "&sig=" + urlEncode(String((char*)sig).substring(0, sigLen)) +
         "&se=" + String(sasExpiry);
}

// ------------------------------------------------------------- Propiedades
void reportProps(JsonDocument& doc) {
  String out; serializeJson(doc, out);
  String topic = "$iothub/twin/PATCH/properties/reported/?$rid=" + String(twinRid++);
  mqtt.publish(topic.c_str(), out.c_str());
  Serial.printf("[TWIN] reported %s\n", out.c_str());
}

void ackWritable(const char* name, float value, int version) {
  JsonDocument d;
  d[name]["value"] = value; d[name]["ac"] = 200; d[name]["ad"] = "aplicado"; d[name]["av"] = version;
  reportProps(d);
}

void applyDesired(JsonVariant desired) {
  int ver = desired["$version"] | 1;
  if (desired["sampleIntervalS"].is<int>()) {
    int v = desired["sampleIntervalS"];
    if (v >= 5 && v <= 3600) sampleIntervalS = v;
    ackWritable("sampleIntervalS", sampleIntervalS, ver);
  }
  if (desired["intakeAlarmC"].is<float>()) {
    intakeAlarmC = constrain((float)desired["intakeAlarmC"], 18.0f, 35.0f);
    ackWritable("intakeAlarmC", intakeAlarmC, ver);
  }
}

// ---------------------------------------------------------------- Mensajes
void onMessage(char* topic, byte* payload, unsigned int len) {
  String t(topic);
  String body; body.reserve(len);
  for (unsigned int i = 0; i < len; i++) body += (char)payload[i];
  Serial.printf("[RX] %s %s\n", topic, body.c_str());

  if (t.startsWith("$iothub/methods/POST/")) {
    String name = t.substring(21, t.indexOf('/', 21));
    String rid = t.substring(t.indexOf("$rid=") + 5);
    JsonDocument req; deserializeJson(req, body);
    JsonDocument res; int status = 200;
    if (name == "setFanBoost") {
      fanBoost = req.is<bool>() ? req.as<bool>() : (bool)(req["on"] | true);
      digitalWrite(PIN_RELAY, fanBoost);
      res["fanBoost"] = fanBoost;
      JsonDocument p; p["fanBoostState"] = fanBoost;
      String out; serializeJson(res, out);
      mqtt.publish(("$iothub/methods/res/200/?$rid=" + rid).c_str(), out.c_str());
      reportProps(p);
      return;
    } else if (name == "simulateOutage") {
      int s = req.is<int>() ? req.as<int>() : (int)(req["seconds"] | 120);
      s = constrain(s, 30, 1800);
      res["outageSeconds"] = s;
      outageUntil = millis() + (uint32_t)s * 1000UL;
    } else { status = 404; res["error"] = "comando no implementado"; }
    String out; serializeJson(res, out);
    mqtt.publish(("$iothub/methods/res/" + String(status) + "/?$rid=" + rid).c_str(), out.c_str());
    if (outageUntil) {
      mqtt.loop(); delay(500);
      Serial.println("=== DESCONEXIÓN CONTROLADA === (MQTT DISCONNECT)");
      mqtt.disconnect(); digitalWrite(PIN_LED_NET, LOW);
    }
  } else if (t.startsWith("$iothub/twin/res/200")) {        // GET twin completo
    JsonDocument d; deserializeJson(d, body);
    applyDesired(d["desired"]);
  } else if (t.startsWith("$iothub/twin/PATCH/properties/desired/")) {
    JsonDocument d; deserializeJson(d, body);
    applyDesired(d.as<JsonVariant>());
  }
}

// ------------------------------------------------------------------ Red
void connectWiFi() {
  Serial.print("[WIFI] Conectando a Wokwi-GUEST");
  WiFi.begin("Wokwi-GUEST", "", 6);
  while (WiFi.status() != WL_CONNECTED) { delay(250); Serial.print("."); }
  Serial.printf(" OK IP=%s\n", WiFi.localIP().toString().c_str());
  configTime(0, 0, "pool.ntp.org", "time.google.com");    // SAS requiere hora UTC real
  while (time(nullptr) < 1700000000) delay(200);
}

bool connectHub() {
  Serial.printf("[MQTT] Connecting -> %s:8883\n", IOT_HUB_HOST);
  sas = makeSas(3600);
  username = String(IOT_HUB_HOST) + "/" + DEVICE_ID + "/?api-version=2021-04-12&model-id=" + urlEncode(MODEL_ID);
  if (!mqtt.connect(DEVICE_ID, username.c_str(), sas.c_str())) {
    Serial.printf("[MQTT] fallo rc=%d\n", mqtt.state());
    return false;
  }
  Serial.println("[MQTT] Connected");
  digitalWrite(PIN_LED_NET, HIGH);
  mqtt.subscribe("$iothub/methods/POST/#");
  mqtt.subscribe("$iothub/twin/res/#");
  mqtt.subscribe("$iothub/twin/PATCH/properties/desired/#");
  mqtt.publish("$iothub/twin/GET/?$rid=0", "");
  JsonDocument p;
  p["firmwareVersion"] = FW_VER; p["sourceOrigin"] = "wokwi-esp32-arduino";
  p["fanBoostState"] = fanBoost;
  reportProps(p);
  return true;
}

// ---------------------------------------------------------------- Telemetría
void sendTelemetry() {
  TempAndHumidity th = dht.getTempAndHumidity();
  ds.requestTemperatures();
  float intake = th.temperature + INTAKE_OFFSET;
  float hr = th.humidity + HR_OFFSET;
  float exhaust = ds.getTempCByIndex(0) + EXHAUST_OFFSET;
  if (isnan(intake) || intake < T_VALID_MIN || intake > T_VALID_MAX) { Serial.println("[SENS] DHT22 fuera de rango"); return; }
  bool over = intake > intakeAlarmC;
  digitalWrite(PIN_LED_ALM, over);

  JsonDocument d;
  d["tempIntake"] = roundf(intake * 10) / 10.0;
  d["tempExhaust"] = roundf(exhaust * 10) / 10.0;
  d["humidity"] = roundf(hr * 10) / 10.0;
  d["deltaT"] = roundf((exhaust - intake) * 10) / 10.0;
  d["overTemp"] = over;
  String out; serializeJson(d, out);
  String topic = String("devices/") + DEVICE_ID + "/messages/events/$.ct=application%2Fjson&$.ce=utf-8";
  bool ok = mqtt.publish(topic.c_str(), out.c_str());
  Serial.printf("[TX #%lu] %s %s\n", (unsigned long)++txCount, ok ? "OK" : "FAIL", out.c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_RELAY, OUTPUT); pinMode(PIN_LED_ALM, OUTPUT); pinMode(PIN_LED_NET, OUTPUT);
  dht.setup(PIN_DHT, DHTesp::DHT22);
  ds.begin();
  connectWiFi();
  if (strlen(AZURE_ROOT_CA) > 0) tls.setCACert(AZURE_ROOT_CA);   // DigiCert Global Root G2
  else { tls.setInsecure(); Serial.println("[TLS] AVISO: sin validación de CA (solo simulador)"); }
  mqtt.setServer(IOT_HUB_HOST, 8883);
  mqtt.setBufferSize(1024);
  mqtt.setKeepAlive(60);
  mqtt.setCallback(onMessage);
  connectHub();
}

void loop() {
  if (outageUntil) {                                   // hueco controlado
    if ((int32_t)(millis() - outageUntil) < 0) { delay(200); return; }
    outageUntil = 0; Serial.println("=== RECONEXIÓN ===");
  }
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if ((uint32_t)time(nullptr) > sasExpiry - 300) mqtt.disconnect();   // renovar SAS
  if (!mqtt.connected()) {
    digitalWrite(PIN_LED_NET, LOW);
    if (!connectHub()) { delay(5000); return; }
  }
  mqtt.loop();
  if (millis() - lastTx >= sampleIntervalS * 1000UL || lastTx == 0) {
    lastTx = millis();
    sendTelemetry();
  }
}
