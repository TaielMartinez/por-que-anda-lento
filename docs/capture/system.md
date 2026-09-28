# Dominio `system`

Parte de la **Foto**. Carpeta: `snapshot/system/`. Contexto general de la PC: con qué hardware y qué Windows se está trabajando.

## Archivos

### `hardware`: ¿Qué CPU, RAM, placa, BIOS y GPU tiene la PC?

- `computer`: fabricante y modelo.
- `cpu`: `name`, `cores`, `logical_processors`, `max_clock_mhz`, `current_clock_mhz`, `l2_cache_kb`, `l3_cache_kb`.
- `ram.total_bytes`: RAM que ve Windows.
- `ram.modules[]`: `slot`, `bank`, `capacity_bytes`, `speed_mhz` (velocidad nominal del módulo según SPD), `configured_speed_mhz` (velocidad a la que corre), `manufacturer`, `part_number`.
- `motherboard`: `manufacturer`, `product`, `version`.
- `bios`: `manufacturer`, `version`, `release_date`.
- `gpus[]`: `name`, `driver_version`, `driver_date`, `adapter_ram_bytes_wmi` (WMI lo trunca en 4 GB o menos: no usarlo para la VRAM real), `resolution`, `refresh_rate_hz`.

**Cómo interpretarlo**
- Si `configured_speed_mhz` es mucho menor que la velocidad que figura en el `part_number` (por ejemplo, un kit "3000" a 2133), probablemente XMP/DOCP no está activado en el BIOS.
- Módulos de distinta capacidad o `part_number` mezclados pueden impedir el dual channel completo.
- Un BIOS con `release_date` muy vieja puede tener problemas de estabilidad o microcódigo ya corregidos.

### `os`: ¿Qué versión de Windows corre, desde cuándo está encendida y cómo está el archivo de paginación?

- `caption`, `version`, `build`, `architecture`, `installed_at`.
- `last_boot_at`, `uptime_hours`: con el inicio rápido de Windows, apagar no reinicia el kernel. Un uptime de muchos días es normal ahí, y deja acumular fugas de drivers.
- `pagefiles[]`: `path`, `allocated_mb`, `current_usage_mb`, `peak_usage_mb`.

### `power`: ¿Qué plan y modo de energía están activos?

- `active_plan.guid` y `active_plan.name` (el nombre viene en el idioma de Windows).
- `power_mode_overlay`: el "modo de energía" de Windows 11: `best_power_efficiency`, `balanced`, `best_performance`, o el GUID si no se reconoce. `null` si Windows no usa overlays.

### `graphics_settings`: ¿Están activos Game Mode y la programación de GPU acelerada por hardware (HAGS)?

- `hardware_accelerated_gpu_scheduling`: `true` / `false`; `null` si el valor no está en el registro (Windows decide según el driver).
- `game_mode`: `true` / `false`.
- `game_mode_is_default`: `true` si no hay valor explícito (Windows lo deja activo por defecto).

## Sección del Resumen (`summary.system`)

| Campo | Qué es |
|---|---|
| `cpu` | Nombre de la CPU. |
| `logical_processors` | Hilos lógicos. |
| `ram_total_bytes` | RAM total visible. |
| `os_build` | Build de Windows. |
| `uptime_hours` | Horas desde el último arranque del kernel. |
| `power_plan` | Nombre del plan de energía activo. |
