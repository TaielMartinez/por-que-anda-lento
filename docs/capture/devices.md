# Dominio `devices`

Parte de la **Foto**. Carpeta: `snapshot/devices/`. Qué tiene conectado la PC y qué dispositivos fallan.

Campos de cada dispositivo: `name`, `class` (clase PnP: `Mouse`, `Display`, `USB`, `AudioEndpoint`...), `manufacturer`, `status`, `error_code`, `error_meaning`, `pnp_id`, `present`.

## Archivos

### `all`: ¿Qué dispositivos reconoce Windows?

Todos los dispositivos PnP presentes, ordenados por clase y nombre.

### `problems`: ¿Qué dispositivos tienen un error en el Administrador de dispositivos y cuál?

Los que tienen `error_code` distinto de 0. `error_meaning` traduce los códigos frecuentes: 10 (no puede iniciar), 28 (sin drivers), 43 (Windows lo detuvo por fallas), 22 (deshabilitado). Un dispositivo que falla puede generar interrupciones y reintentos que traban el sistema.

### `usb`: ¿Qué dispositivos USB y HID (mouse, teclado, joystick) hay conectados?

Dispositivos con `pnp_id` `USB\...` o `HID\...`, o de clase `USB`. Sirve para asociar el Síntoma "el mouse salta" con el hardware concreto, por ejemplo un receptor inalámbrico o un hub.

## Sección del Resumen (`summary.devices`)

| Campo | Qué es |
|---|---|
| `count` | Dispositivos presentes. |
| `usb_count` | Dispositivos USB/HID. |
| `problem_devices` | Nombres de los dispositivos con error. |
