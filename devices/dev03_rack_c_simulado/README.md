# DEV-03 · Rack C · Origen: Digital Twin / simulador nativo de IoT Central

No hay código del grupo: el dispositivo se crea en IoT Central sobre la plantilla
`RackThermal` (templates/RackThermal.json) con la opción **Simulate this device = Yes**.

1. Devices > + New > Template: *Rack térmico (A/B/C)* · Device ID: `dc-rack-c-sim` · Simulate: **Yes**.
2. Verificar en la vista *Overview* que llega telemetría periódica (estado **Connected**).
3. Editar la propiedad escribible `intakeAlarmC` o `sampleIntervalS` desde la vista *Properties*
   (evidencia de "propiedades editables").
4. Ejecutar el comando `setFanBoost` desde la vista *Commands* (el simulador responde).

Limitación documentada: los valores del simulador son aleatorios dentro del esquema
y la cadencia la fija la plataforma; sirve como gemelo de referencia para comparar
con Rack A (Python) y Rack B (Wokwi), que sí siguen un perfil físico.
