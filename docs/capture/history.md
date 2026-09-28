# Historial (`history`)

Carpeta: `history/`. Eventos de Windows de los **últimos 7 días**, un archivo por fuente, con un máximo de 200 por fuente (los más recientes). Sirve para ver si el Síntoma es un patrón o un caso aislado.

## Estructura de cada archivo

```json
{"log": "System", "days": 7, "max_events": 200, "truncated": false, "events": [ ... ]}
```

Cada evento tiene:
- `provider`: quién lo registró.
- `event_id`.
- `level`: 1 crítico, 2 error, 3 advertencia, 4 información.
- `time_created`: hora local.
- `record_id`.
- `data`: los campos del evento.
- `message`: el texto en el idioma de Windows, o `null` si el proveedor no lo registra.

Si `truncated` es `true`, hubo al menos 200 eventos y el manifest lo indica en `note`. Si la fuente no se pudo leer, el archivo queda `partial` con el motivo.

## Fuentes

### `disk`: ¿Hubo errores o advertencias de disco o del sistema de archivos?

Proveedores `disk`, `Ntfs`, `stornvme`, `storahci` y `volmgr`, con nivel de advertencia o peor. El `disk` 7 (bloque dañado) y el 153 (reintentos de I/O) indican un disco que falla. El `disk` 51 indica un error de paginación.

### `whea`: ¿Hubo errores de hardware reportados por WHEA (CPU, RAM, PCIe)?

Cualquier evento de `WHEA-Logger` merece atención. Los corregidos (ID 17, 19, 47) suelen deberse a PCIe o a RAM y overclock inestables. Los fatales (ID 1, 18) terminan en pantalla azul.

### `resource_exhaustion`: ¿Windows detectó que se quedaba sin memoria virtual?

El ID 2004 aparece cuando la memoria comprometida se acerca al límite. El `data` indica qué procesos consumían más.

### `diagnostics_performance`: ¿Hubo arranques, apagados o suspensiones lentos, y qué los demoró?

El canal `Diagnostics-Performance/Operational` necesita admin. Los ID 100–110 son de arranque, 200–203 de apagado y 300–302 de suspensión. El `data` suele nombrar el driver, servicio o app que causó la demora.

### `gpu_tdr`: ¿El driver de video dejó de responder y se reinició (TDR)?

`Display` 4101 y los eventos de `nvlddmkm` y `amdkmdag`. Coinciden con pantallas negras breves, congelamientos o juegos que se cierran.

### `unexpected_shutdowns`: ¿Hubo apagados o reinicios inesperados (cuelgues, cortes)?

`Kernel-Power` 41 (el sistema se reinició sin apagarse limpio) y `EventLog` 6008. Si `BugcheckCode` es distinto de 0, fue una pantalla azul. Si es 0, fue un corte de energía, un reset o un cuelgue total.

### `app_crashes`: ¿Qué aplicaciones se cerraron solas o se colgaron?

`Application Error` 1000 (cierre inesperado, con el módulo culpable en `data`) y `Application Hang` 1002.

## Sección del Resumen (`summary.history`)

Una entrada por fuente con:
- `total`: cantidad de eventos, o `null` si la fuente no se pudo leer.
- `by_day`: cantidad por fecha (`AAAA-MM-DD`).
- `truncated`.
