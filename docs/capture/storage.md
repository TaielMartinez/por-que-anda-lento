# Dominio `storage`

Parte de la **Foto**. Carpeta: `snapshot/storage/`. Discos y espacio libre.

## Archivos

### `volumes`: ¿Cuánto espacio libre queda en cada volumen?

`mountpoint`, `fstype`, `total_bytes`, `used_bytes`, `free_bytes`, `free_percent`, `error` (si no se pudo leer). Con menos de 10 % libre en el disco del sistema, Windows pagina y actualiza peor, y un SSD pierde rendimiento de escritura.

### `physical_disks`: ¿Qué discos físicos hay, de qué tipo y en qué estado de salud?

`device_id`, `name`, `media_type` (`HDD`, `SSD`, `SCM`), `bus_type` (`NVMe`, `SATA`, `USB`...), `size_bytes`, `health_status` (`healthy`, `warning`, `unhealthy`, `unknown`), `operational_status`, `firmware`. Si el sistema está en un HDD, eso solo ya explica mucha lentitud.

### `smart`: ¿Qué dicen los contadores de confiabilidad (SMART) de cada disco: temperatura, desgaste, errores?

Una fila por disco. `device_id` coincide con `physical_disks`. Campos: `temperature_c`, `temperature_max_c`, `wear_percent` (desgaste del SSD: 100 = agotado), `read_errors_total`, `read_errors_uncorrected`, `write_errors_total`, `write_errors_uncorrected`, `power_on_hours`, `start_stop_cycles`. Necesita admin: sin permisos queda `partial` y vacío. Los errores no corregidos por encima de 0 son graves. Un SSD NVMe por encima de 70 °C hace throttling.

## Sección del Resumen (`summary.storage`)

| Campo | Qué es |
|---|---|
| `lowest_free_percent` | El volumen con menos espacio libre (`mountpoint`, `free_percent`). |
| `disks_not_healthy` | Discos cuya salud no es `healthy`. |
| `max_wear_percent` | Mayor desgaste entre los SSD. |
| `uncorrected_errors` | Suma de errores de lectura y escritura no corregidos. |
