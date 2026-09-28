# Dominio `security`

Parte de la **Foto**. Carpeta: `snapshot/security/`. Los antivirus son una causa frecuente de lentitud transitoria: escaneos completos, análisis en tiempo real de carpetas con muchos archivos, o dos antivirus activos a la vez.

## Archivos

### `defender_status`: ¿Defender está activo y está escaneando ahora?

- `running_mode`: `Normal`, o `Passive Mode` si hay otro antivirus.
- `antivirus_enabled`, `realtime_protection`.
- `scan_in_progress`: `quick`, `full` o `null`. Se deduce de que el último escaneo empezó y no terminó.
- `last_quick_scan` y `last_full_scan`, con su `start` y su `end`.
- `signature_age_days`.

### `defender_exclusions`: ¿Qué rutas, procesos y extensiones excluye Defender?

`paths`, `processes`, `extensions`. Leerlas necesita admin: sin permisos queda `partial`.

### `antivirus_products`: ¿Qué antivirus están registrados y cuáles están activos?

Desde el Centro de seguridad: `name`, `enabled`, `definitions_up_to_date`, `product_state` (el valor crudo) y `executable`. Dos productos con `enabled: true` al mismo tiempo pueden duplicar el costo de cada acceso a disco.

## Sección del Resumen (`summary.security`)

| Campo | Qué es |
|---|---|
| `defender_realtime` | Protección en tiempo real activa. |
| `defender_scan_in_progress` | `quick`, `full` o `null`. |
| `antivirus_active` | Antivirus activos. |
