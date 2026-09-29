/*
 * DEV-10 · Puerta de sala / control de acceso · Origen: SEGUNDA instancia Wokwi
 * (ESP32, sketch y circuito distintos de DEV-02). Envío POR EVENTO + latido 600 s.
 *
 * Hardware simulado:
 *   Interruptor deslizante  = contacto magnético de puerta (reed NC tipo MC-38)
 *   Pulsador verde          = lectura de credencial válida (lector RFID 13.56 MHz)
 *   Pulsador rojo           = credencial rechazada
 *   LED azul                = cerradura electromagnética liberada (comando unlockDoor)
 *   Buzzer                  = puerta abierta > doorHeldAlarmS (escribible)
 *
 * Telemetría: doorOpen, doorOpenSeconds, accessGranted, accessDenied (conteos del
 *             intervalo -> SUMATORIA diaria = eventos de acceso por día)
 * Comando   : unlockDoor(int s)     Writable: doorHeldAlarmS
 * Versión   : 1.0.0
 */
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "mbedtls/md.h"
#include "mbedtls/base64.h"
#include "secrets.h"

#define PIN_DOOR     13   // slide switch (HIGH = abierta)
#define PIN_GRANT    12
#define PIN_DENY     14
#define PIN_LOCK_LED 25
#define PIN_BUZZER   33

static const char* MODEL_ID = "dtmi:plk6v9d:prxhobho;1";
static const uint32_t HEARTBEAT_S = 600;

WiFiClientSecure tls;
PubSubClient mqtt(tls);
uint32_t lastOpenTx = 0, sasExpiry = 0, lastHb = 0, openSince = 0, unlockUntil = 0, rid = 1;
uint16_t granted = 0, denied = 0, doorHeldAlarmS = 120;
bool doorOpen = false, lastGrantBtn = HIGH, lastDenyBtn = HIGH;
String sas, username;

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
  uint8_t key[64]; size_t kl = 0;
  mbedtls_base64_decode(key, sizeof(key), &kl, (const uint8_t*)DEVICE_KEY_B64, strlen(DEVICE_KEY_B64));
  uint8_t h[32];
  mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), key, kl,
                  (const uint8_t*)toSign.c_str(), toSign.length(), h);
  uint8_t sig[64]; size_t sl = 0;
  mbedtls_base64_encode(sig, sizeof(sig), &sl, h, 32);
  return "SharedAccessSignature sr=" + uri + "&sig=" + urlEncode(String((char*)sig).substring(0, sl)) +
         "&se=" + String(sasExpiry);
}

void publishState(const char* reason) {
  JsonDocument d;
  d["doorOpen"] = doorOpen;
  d["doorOpenSeconds"] = doorOpen ? (millis() - openSince) / 1000 : 0;
  d["accessGranted"] = granted;
  d["accessDenied"] = denied;
  d["eventReason"] = reason;
  String out; serializeJson(d, out);
  String topic = String("devices/") + DEVICE_ID + "/messages/events/$.ct=application%2Fjson&$.ce=utf-8";
  bool ok = mqtt.publish(topic.c_str(), out.c_str());
  Serial.printf("[TX %s] %s %s\n", reason, ok ? "OK" : "FAIL", out.c_str());
  if (ok) { granted = 0; denied = 0; }      // conteos por intervalo (sumables)
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  String t(topic), body;
  for (unsigned int i = 0; i < len; i++) body += (char)payload[i];
  Serial.printf("[RX] %s %s\n", topic, body.c_str());
  if (t.startsWith("$iothub/methods/POST/unlockDoor")) {
    String r = t.substring(t.indexOf("$rid=") + 5);
    JsonDocument req; deserializeJson(req, body);
    int s = constrain(req.is<int>() ? req.as<int>() : (int)(req["seconds"] | 5), 1, 30);
    unlockUntil = millis() + s * 1000UL;
    digitalWrite(PIN_LOCK_LED, HIGH);
    String out = "{\"unlockedSeconds\":" + String(s) + "}";
    mqtt.publish(("$iothub/methods/res/200/?$rid=" + r).c_str(), out.c_str());
    publishState("cmd:unlockDoor");
  } else if (t.startsWith("$iothub/methods/POST/")) {
    String r = t.substring(t.indexOf("$rid=") + 5);
    mqtt.publish(("$iothub/methods/res/404/?$rid=" + r).c_str(), "{\"error\":\"no implementado\"}");
  } else if (t.startsWith("$iothub/twin/PATCH/properties/desired/")) {
    JsonDocument d; deserializeJson(d, body);
    if (d["doorHeldAlarmS"].is<int>()) {
      doorHeldAlarmS = constrain((int)d["doorHeldAlarmS"], 30, 900);
      String ack = "{\"doorHeldAlarmS\":{\"value\":" + String(doorHeldAlarmS) +
                   ",\"ac\":200,\"ad\":\"aplicado\",\"av\":" + String((int)(d["$version"] | 1)) + "}}";
      mqtt.publish(("$iothub/twin/PATCH/properties/reported/?$rid=" + String(rid++)).c_str(), ack.c_str());
    }
  }
}

bool connectHub() {
  sas = makeSas(3600);
  username = String(IOT_HUB_HOST) + "/" + DEVICE_ID + "/?api-version=2021-04-12&model-id=" + urlEncode(MODEL_ID);
  Serial.printf("[MQTT] Connecting -> %s\n", IOT_HUB_HOST);
  if (!mqtt.connect(DEVICE_ID, username.c_str(), sas.c_str())) { Serial.printf("rc=%d\n", mqtt.state()); return false; }
  mqtt.subscribe("$iothub/methods/POST/#");
  mqtt.subscribe("$iothub/twin/PATCH/properties/desired/#");
  String p = String("{\"firmwareVersion\":\"1.0.0\",\"sourceOrigin\":\"wokwi-esp32-door\"}");
  mqtt.publish(("$iothub/twin/PATCH/properties/reported/?$rid=" + String(rid++)).c_str(), p.c_str());
  Serial.println("[MQTT] Connected");
  publishState("boot");
  return true;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_DOOR, INPUT_PULLUP); pinMode(PIN_GRANT, INPUT_PULLUP); pinMode(PIN_DENY, INPUT_PULLUP);
  pinMode(PIN_LOCK_LED, OUTPUT); pinMode(PIN_BUZZER, OUTPUT);
  WiFi.begin("Wokwi-GUEST", "", 6);
  while (WiFi.status() != WL_CONNECTED) delay(250);
  configTime(0, 0, "pool.ntp.org");
  while (time(nullptr) < 1700000000) delay(200);
  if (strlen(AZURE_ROOT_CA) > 0) tls.setCACert(AZURE_ROOT_CA); else tls.setInsecure();
  mqtt.setServer(IOT_HUB_HOST, 8883);
  mqtt.setBufferSize(1024);
  mqtt.setCallback(onMessage);
  connectHub();
  lastHb = millis();
}

void loop() {
  if ((uint32_t)time(nullptr) > sasExpiry - 300) mqtt.disconnect();
  if (!mqtt.connected() && !connectHub()) { delay(5000); return; }
  mqtt.loop();

  bool nowOpen = digitalRead(PIN_DOOR) == HIGH;
  if (nowOpen != doorOpen) {
    doorOpen = nowOpen;
    if (doorOpen) { openSince = millis(); lastOpenTx = millis(); }
    publishState(doorOpen ? "event:door_open" : "event:door_closed");
  }
  bool g = digitalRead(PIN_GRANT), n = digitalRead(PIN_DENY);
  if (g == LOW && lastGrantBtn == HIGH) { granted++; unlockUntil = millis() + 5000; digitalWrite(PIN_LOCK_LED, HIGH); publishState("event:access_granted"); }
  if (n == LOW && lastDenyBtn == HIGH)  { denied++;  publishState("event:access_denied"); }
  lastGrantBtn = g; lastDenyBtn = n;

  if (unlockUntil && (int32_t)(millis() - unlockUntil) >= 0) { unlockUntil = 0; digitalWrite(PIN_LOCK_LED, LOW); }
  bool held = doorOpen && (millis() - openSince) / 1000 > doorHeldAlarmS;
  digitalWrite(PIN_BUZZER, held);
  // Mientras la puerta está abierta se reporta cada 30 s para que la Rule
  // "doorOpenSeconds > 120" de IoT Central pueda dispararse.
  if (doorOpen && millis() - lastOpenTx >= 30000UL) { lastOpenTx = millis(); publishState("door_open_update"); }

  if (millis() - lastHb >= HEARTBEAT_S * 1000UL) { lastHb = millis(); publishState("heartbeat"); }
  delay(30);
}
