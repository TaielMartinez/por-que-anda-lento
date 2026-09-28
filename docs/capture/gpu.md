# Dominio `gpu`

Parte de la **Foto**. Carpeta: `snapshot/gpu/`. Estado de la placa de video y qué procesos la usan. La serie temporal y el top por proceso de cada muestra están en la Ventana de muestreo (`sampling/gpu`, `sampling/processes_top_gpu`).

Fuentes:
- **nvidia-smi** (viene con el driver NVIDIA): temperatura, clocks, consumo y motivos de limitación.
- **Contadores de Windows** (`GPU Engine`, `GPU Process Memory`): uso por proceso con cualquier fabricante. Sin NVIDIA son la única fuente.

## Archivos

### `adapters`: ¿Qué uso, memoria, temperatura, clocks y limitaciones tiene la GPU?

Con `source: "nvidia-smi"`, `gpus[]` tiene:

| Campo | Qué es |
|---|---|
| `name`, `driver_version` | Placa y versión del driver. |
| `pstate` | Estado de energía: `P0` es el máximo rendimiento y `P8`, reposo. |
| `temperature_c`, `fan_percent` | Temperatura y ventilador. |
| `utilization_percent`, `memory_utilization_percent` | Uso del núcleo y del controlador de memoria. |
| `memory_total_bytes`, `memory_used_bytes` | VRAM. |
| `graphics_clock_mhz`, `memory_clock_mhz`, `max_graphics_clock_mhz` | Clocks actuales y el máximo del núcleo. |
| `power_draw_w`, `power_limit_w` | Consumo actual y límite. |
| `clock_event_reasons` | Por qué la GPU no está al máximo clock (ver abajo). |
| `pcie_gen`, `pcie_width` | Enlace PCIe actual (en reposo baja de generación: es normal). |

Motivos (`clock_event_reasons`):
- `gpu_idle`: sin carga. Normal.
- `sw_power_cap`: llegó al límite de consumo.
- `sw_thermal_slowdown`, `hw_thermal_slowdown`: **limitada por temperatura**.
- `hw_slowdown`, `hw_power_brake_slowdown`: limitada por la fuente o por una señal del hardware, lo que indica un problema de alimentación.
- `applications_clocks_setting`, `display_clock_setting`, `sync_boost`: ajustes.

Con `source: "counters"` (sin nvidia-smi), `adapters[]` solo tiene `luid` y `dedicated_memory_used_bytes`, y el archivo queda `partial`.

### `processes`: ¿Qué procesos usan la GPU, cuánto (motor más cargado) y cuánta memoria de video?

`pid`, `name`, `gpu_percent`, `busiest_engine` y `dedicated_memory_bytes`, ordenado por uso.
- `gpu_percent`: el uso del motor más cargado (`3D`, `Copy`, `VideoDecode`, `Compute`...), igual que la columna GPU del Administrador de tareas.
- `busiest_engine`: cuál fue ese motor.
- `dedicated_memory_bytes`: VRAM dedicada del proceso.

Un navegador o un overlay con uso de `3D` alto mientras el usuario no juega es sospechoso.

## Sección del Resumen (`summary.gpu`)

| Campo | Qué es |
|---|---|
| `source` | `nvidia-smi` o `counters`. |
| `name`, `utilization_percent`, `temperature_c`, `memory_used_bytes`, `memory_total_bytes`, `clock_event_reasons` | De la primera GPU. |
| `top_processes` | Los 5 procesos que más usan la GPU. |
