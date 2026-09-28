# Dominio `drivers`

Parte de la **Foto**. Carpeta: `snapshot/drivers/`. Los drivers son la causa típica de la latencia DPC (mouse que salta, audio cortado) y de las fugas del pool no paginado (RAM que "no aparece").

## Archivos

### `loaded`: ¿Qué drivers de kernel están cargados?

`name`, `display_name`, `start_mode`, `path`. `name` coincide con el nombre de módulo que aparece en `sampling/dpc_isr_by_driver` (sin `.sys`).

### `device_drivers`: ¿Qué versión y fecha tiene el driver de cada dispositivo?

`device`, `provider`, `version`, `date` (`AAAA-MM-DD`), `signed`, `inf`. Ordenado del más viejo al más nuevo. Para comparar con el `driver_version` de la GPU en `snapshot/system/hardware`, o para detectar drivers de chipset, audio o red de hace años.

### `unsigned`: ¿Qué drivers no tienen una firma digital válida?

Con la Preparación hecha, sale de Sysinternals Sigcheck sobre `C:\Windows\System32\drivers`, con `path`, `verified`, `company`, `description`, `file_version` y `date`. Sin Sigcheck, sale de lo que Windows informa sobre los drivers de dispositivos (`device`, `provider`, `version`, `inf`) y queda `partial`.

## Sección del Resumen (`summary.drivers`)

| Campo | Qué es |
|---|---|
| `loaded_count` | Drivers cargados. |
| `unsigned` | Drivers sin firma válida (rutas, o nombres de dispositivo sin Sigcheck). |
| `oldest_third_party` | Los 5 drivers de dispositivos más viejos que no son de Microsoft. |
