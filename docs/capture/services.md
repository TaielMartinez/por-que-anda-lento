# Dominio `services`

Parte de la **Foto**. Carpeta: `snapshot/services/`.

Campos de cada servicio:
- `name` y `display_name`.
- `state`: `Running`, `Stopped`, etc.
- `start_mode`: `Auto`, `Manual` o `Disabled`.
- `pid`: el proceso que lo hospeda. Varios servicios comparten un `svchost.exe`: cruzar con `snapshot/processes/list` por `pid` para ver cuánto consume.
- `account`: la cuenta con la que corre.
- `command`: el ejecutable con sus argumentos.

## Archivos

### `list`: ¿Qué servicios existen, en qué estado están y cómo arrancan?

Todos, ordenados por nombre.

### `running`: ¿Qué servicios están corriendo ahora y en qué proceso?

Solo los que están en `Running`. Conviene buscar servicios de terceros que no hacen falta todo el tiempo: actualizadores, telemetría, utilidades de RGB o periféricos, clientes de juegos.

## Sección del Resumen (`summary.services`)

| Campo | Qué es |
|---|---|
| `count`, `running_count`, `auto_start_count` | Totales. |
| `auto_start_not_running` | Servicios automáticos detenidos. Muchos son normales (arranque por demanda o demorado); importa si uno esperable está caído o se reinicia en bucle. |
