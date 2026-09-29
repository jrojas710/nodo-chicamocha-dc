#!/usr/bin/env node
/**
 * DEV-08 · Detección de humo / incendio · Origen: REPLAY de CSV histórico con
 * Node.js + azure-iot-device-amqp (AMQPS, TLS puerto 5671). Tercer protocolo de la
 * flota (MQTT, MQTT-WS, AMQP, HTTPS).
 *
 * data/humo_historico.csv es un perfil de prueba de 24 h (720 filas, paso 120 s)
 * construido sobre los rangos de sensibilidad de UL 268 (0.5–4.0 %/ft). Incluye una
 * pre-alarma (polvo en mantenimiento) y una alarma (prueba de humo en cuarto UPS).
 * El replay respeta el paso original (120 s) y registra la fila fuente (replayRow).
 *
 * Comando: silenceAlarm (silencia la sirena local 300 s; la alarma sigue registrada)
 * Versión: 1.0.0
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const { ProvisioningDeviceClient } = require('azure-iot-provisioning-device');
const { Amqp: ProvAmqp } = require('azure-iot-provisioning-device-amqp');
const { SymmetricKeySecurityClient } = require('azure-iot-security-symmetric-key');
const { Client, Message } = require('azure-iot-device');
const { Amqp } = require('azure-iot-device-amqp');

const DEVICE_ID = 'dc-smoke-replay';
const MODEL_ID = 'dtmi:orujaybg:tcp7bhfw;1';
const INTERVAL_S = 120;
const DPS_HOST = process.env.IOTC_DPS_HOST || 'global.azure-devices-provisioning.net';
const START_ROW = parseInt(process.env.REPLAY_START_ROW || '-1', 10); // -1 = alinear a la hora local

function log(level, msg, obj) {
  const line = `${new Date().toISOString()} | ${level.padEnd(7)} | ${DEVICE_ID} | ${msg}` +
    (obj ? ' ' + JSON.stringify(obj) : '');
  console.log(line);
  fs.mkdirSync('logs', { recursive: true });
  fs.appendFileSync(path.join('logs', `${DEVICE_ID}.log`), line + '\n');
}

function deviceKey() {
  const specific = process.env['IOTC_DEVICE_KEY_' + DEVICE_ID.toUpperCase().replace(/-/g, '_')];
  if (specific) return specific;
  const group = process.env.IOTC_GROUP_KEY;
  if (!group) throw new Error('Falta IOTC_GROUP_KEY en el entorno (.env)');
  return crypto.createHmac('sha256', Buffer.from(group, 'base64'))
    .update(DEVICE_ID, 'utf8').digest('base64');
}

function loadCsv() {
  const lines = fs.readFileSync(path.join(__dirname, 'data', 'humo_historico.csv'), 'utf8')
    .trim().split(/\r?\n/);
  const head = lines.shift().split(',');
  return lines.map((l) => Object.fromEntries(l.split(',').map((v, i) => [head[i], Number(v)])));
}

async function main() {
  const idScope = process.env.IOTC_ID_SCOPE;
  if (!idScope) throw new Error('Falta IOTC_ID_SCOPE en el entorno (.env)');
  const key = deviceKey();
  const rows = loadCsv();

  log('INFO', `Connecting | DPS AMQP | scope=${idScope}`);
  const security = new SymmetricKeySecurityClient(DEVICE_ID, key);
  const prov = ProvisioningDeviceClient.create(DPS_HOST, idScope, new ProvAmqp(), security);
  prov.setProvisioningPayload({ modelId: MODEL_ID });
  const reg = await prov.register();
  log('INFO', `DPS asignado -> ${reg.assignedHub}`);

  const client = Client.fromConnectionString(
    `HostName=${reg.assignedHub};DeviceId=${DEVICE_ID};SharedAccessKey=${key}`, Amqp);
  client.on('disconnect', () => log('WARN', 'Disconnected (AMQP)'));
  client.on('error', (e) => log('ERROR', e.message));
  await client.open();
  log('INFO', `Connected | AMQPS:5671 | ${reg.assignedHub}`);

  let silencedUntil = 0;
  client.onDeviceMethod('silenceAlarm', (req, res) => {
    silencedUntil = Date.now() + 300000;
    log('INFO', 'Comando silenceAlarm', req.payload);
    res.send(200, { silencedSeconds: 300 }, () => {});
  });

  const twin = await client.getTwin();
  twin.properties.reported.update({
    firmwareVersion: '1.0.0', sourceOrigin: 'csv-replay-node-amqp',
    replaySource: 'data/humo_historico.csv (720 filas, paso 120 s)',
    lastBoot: new Date().toISOString(),
  }, () => {});

  // Alinea la fila del CSV con la hora local (UTC-5) para que el perfil diario sea coherente.
  let idx = START_ROW >= 0 ? START_ROW
    : Math.floor((((Date.now() / 60000) - 300) % 1440 + 1440) % 1440 / 2) % rows.length;
  let sent = 0;

  const tick = async () => {
    const r = rows[idx];
    const payload = {
      smokeObscuration: r.smokeObscuration,
      ceilingTemp: r.ceilingTemp,
      smokeAlarm: r.smokeAlarm === 1,
      sirenSilenced: Date.now() < silencedUntil,
      replayRow: idx,
    };
    const msg = new Message(JSON.stringify(payload));
    msg.contentType = 'application/json';
    msg.contentEncoding = 'utf-8';
    try {
      await client.sendEvent(msg);
      sent += 1;
      log('INFO', `TX #${sent}`, payload);
    } catch (e) {
      log('ERROR', `Fallo de envío: ${e.message} (hueco en la serie)`);
    }
    idx = (idx + 1) % rows.length;
  };

  await tick();
  const timer = setInterval(tick, INTERVAL_S * 1000);
  process.on('SIGINT', async () => {
    clearInterval(timer);
    log('WARN', 'Detenido por el operador -> cierre AMQP limpio');
    await client.close();
    process.exit(0);
  });
}

main().catch((e) => { log('ERROR', e.stack || e.message); process.exit(1); });
