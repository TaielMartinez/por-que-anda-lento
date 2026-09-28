# Ventana de muestreo (`sampling`)

Carpeta: `sampling/`. El Colector mide el sistema una vez por intervalo durante la duración pedida (por defecto 60 s, cada 1 s; `--duration` e `--interval`). Sirve para ver **picos y tendencias** que una Foto no muestra. Si la duración es 0, no hay Ventana.

Todos los archivos son CSV con una columna `t_s`: segundos desde el inicio de la Ventana. La hora absoluta de inicio está en `manifest.started_at`. Una celda vacía significa "sin dato".

## Sistema

Cada archivo tiene una fila por muestra, incluida la inicial (`t_s = 0`).

### `cpu_per_core`: ¿Cuánto se usó la CPU, en total y por núcleo, en cada momento?

`total_percent` y `core<N>_percent` por núcleo lógico. Un núcleo al 100 % con el total bajo indica un hilo saturado: lo típico de un juego limitado por CPU o de un driver que trabaja en un solo núcleo.

### `dpc_interrupt`: ¿Cuánto tiempo de CPU se fue en DPC e interrupciones de drivers en cada momento?

`dpc_time_percent`, `interrupt_time_percent`, `dpc_rate`, `interrupts_per_s`.

**Cómo interpretarlo.** Los DPC y las interrupciones son trabajo de los drivers que se adelanta a todo lo demás. Picos sostenidos por encima de 1–2 % en total (o de 5–10 % concentrados en un núcleo) causan tirones, audio cortado y un mouse que "salta". Para saber qué driver los genera se necesita la traza ETW (`dpc_isr_by_driver`, si está).

### `disk`: ¿Qué tan ocupado y lento estuvo el disco en cada momento?

`current_queue_length`, `avg_queue_length`, `disk_time_percent`, `disk_bytes_per_s`, `avg_sec_per_transfer` (latencia por operación, en segundos). En un SSD la latencia debería ser menor a 0,01 s. Una cola alta sostenida con latencia alta indica un disco saturado o degradado.

### `page_faults`: ¿Cuántas veces por segundo el sistema tuvo que leer memoria desde disco (hard page faults)?

`page_reads_per_s` (lecturas de disco por falta de página, el indicador de presión de memoria), `pages_input_per_s` (páginas leídas) y `page_faults_per_s` (incluye los soft faults, que son baratos y normalmente altos). Cientos de `page_reads_per_s` sostenidos significan que falta RAM o que hay mucha paginación.

### `memory_available`: ¿Cuánta RAM disponible y memoria comprometida hubo en cada momento?

`available_bytes` y `committed_bytes`. Si la disponible baja de forma constante durante la Ventana, algo está consumiendo memoria.

### `gpu`: ¿Cuánto se usó la GPU y a qué temperatura, clock y consumo estuvo en cada momento?

Columnas: `utilization_percent`, `memory_used_bytes`, `temperature_c`, `graphics_clock_mhz`, `power_draw_w`, `pstate` y `clock_event_reasons` (motivos separados por `|`; ver [gpu.md](gpu.md)). Sin nvidia-smi solo hay uso (el del proceso con el motor más cargado) y memoria, y el archivo queda `partial`.

### `thermals`: ¿Cómo evolucionaron temperaturas, clocks, ventiladores y consumo durante la Ventana?

Una columna por sensor de tipo temperatura, clock, ventilador o potencia, con el nombre `<hardware> / <sensor> [<unidad>]`, por ejemplo `Intel Core i7-8700K / CPU Package [°C]`. Una temperatura que sube mientras los clocks de la CPU bajan es thermal throttling. Sin LibreHardwareMonitor queda vacío y `partial`. Ver [thermals.md](thermals.md).

### `system_load`: ¿Cuántos hilos esperaban CPU y cuántos cambios de contexto hubo en cada momento?

`processor_queue_length`: hilos listos esperando CPU. Si se mantiene por encima de 2 por núcleo, la CPU no alcanza. También `context_switches_per_s`.

## Traza ETW

Con la Preparación hecha (Windows Performance Toolkit), el Colector graba una traza del kernel con xperf exactamente durante la Ventana y la procesa al terminar. El `.etl` crudo se borra, salvo que se pase `--keep-etl`. `manifest.etw` indica `trace` (si hubo traza), `etl_kept` y `etl_path`. Sin WPT, estos dos archivos quedan `failed` y el resto de la Ventana se genera igual.

### `dpc_isr_by_driver`: ¿Qué drivers generaron DPC e interrupciones (ISR), cuántas y cuánto duraron?

Una fila por driver y tipo, sacada de los histogramas de `xperf -a dpcisr`:

| Columna | Qué es |
|---|---|
| `kind` | `dpc` o `isr`. |
| `module` | El driver, por ejemplo `nvlddmkm.sys` (NVIDIA), `ndis.sys` (red), `USBPORT.SYS`/`USBXHCI.SYS` (USB), `storport.sys` (disco), `ACPI.sys`, `dxgkrnl.sys` (gráficos). |
| `count` | Cantidad durante la Ventana. |
| `count_over_100us`, `count_over_1ms` | Cuántas duraron más de 100 µs o de 1 ms. |
| `max_usecs_bucket` | Límite superior del intervalo más lento con eventos: la duración máxima aproximada. |
| `approx_total_usecs` | Tiempo total aproximado (cantidad × punto medio de cada intervalo). |

**Cómo interpretarlo.** Un DPC o ISR de más de 1 ms bloquea ese núcleo y es suficiente para que el mouse "salte" o el audio se corte. Un driver con `count_over_1ms` mayor que 0 de forma repetida es el sospechoso principal. Cruzar `module` con `snapshot/drivers/loaded` y `snapshot/drivers/device_drivers` para ver su versión y fecha.

### `processes_top_net`: ¿Cuáles fueron los 20 procesos que más usaron red en cada muestra?

Desde los eventos TCP/UDP de la traza: `rank`, `pid`, `name`, `sent_bytes_per_s`, `recv_bytes_per_s` y `total_bytes_per_s`. Cada evento se asigna a la muestra que lo cierra.

## Procesos

Las tasas se calculan entre dos muestras consecutivas, así que la primera muestra no genera filas. Un proceso que aparece a mitad de la Ventana no tiene tasa en su primera muestra.

Columnas:

| Columna | Qué es |
|---|---|
| `pid`, `name` | Proceso. |
| `cpu_percent` | % de la CPU **total** (100 % = todos los núcleos al máximo, como en el Administrador de tareas). |
| `private_bytes`, `working_set_bytes` | Memoria en ese momento. |
| `private_bytes_delta` | Cuánto crecieron los private bytes desde la primera vez que se vio el proceso en la Ventana. Un delta positivo y constante es una fuga. |
| `io_read_bytes_per_s`, `io_write_bytes_per_s`, `io_total_bytes_per_s` | I/O por segundo. Windows suma disco, red y dispositivos. |

### `processes_all`: ¿Cuánta CPU, memoria e I/O usó cada proceso en cada muestra (todos los procesos)?

Todos los procesos en cada muestra. Es grande: abrirlo solo si el proceso buscado no aparece en los tops.

### `processes_top_cpu`, `processes_top_ram`, `processes_top_disk`

Los 20 procesos que más usaron cada recurso **en cada muestra**, con una columna `rank`. Los criterios:
- `processes_top_cpu`: por `cpu_percent`.
- `processes_top_ram`: por `private_bytes`, con `private_bytes_delta`.
- `processes_top_disk`: por `io_total_bytes_per_s`.

Un proceso que no entra en el top de una muestra puede estar igual en `processes_all`.

### `processes_top_gpu`

Los 20 procesos que más usaron la GPU en cada muestra: `rank`, `pid`, `name`, `gpu_percent` (motor más cargado), `busiest_engine`, `dedicated_memory_bytes`. Sale de contadores distintos a los de `processes_all`, por eso va aparte.

## Sección del Resumen (`summary.sampling`)

| Campo | Qué es |
|---|---|
| `samples` | Cantidad de muestras. |
| `cpu_total_percent`, `cpu_busiest_core_percent` | `max`, `mean` y `p95` del total y del núcleo más cargado de cada muestra. |
| `dpc_time_percent`, `interrupt_time_percent` | `max`, `mean`, `p95`. |
| `disk_queue_length`, `disk_time_percent` | `max`, `mean`, `p95`. |
| `hard_page_reads_per_s` | `max`, `mean`, `p95` de `page_reads_per_s`. |
| `available_bytes` | `min`, `mean`, `p5` (acá lo malo es lo bajo). |
| `gpu_utilization_percent`, `gpu_temperature_c` | `max`, `mean`, `p95` de la GPU. |
| `temperature_max_c_by_hardware` | Temperatura máxima alcanzada por componente durante la Ventana. |
| `cpu_average_clock_mhz` | `min`, `mean`, `p5` del promedio de clocks de los núcleos (una caída indica throttling). |
| `top_cpu_processes`, `top_ram_processes`, `top_disk_processes`, `top_gpu_processes` | Los 5 procesos con mayor promedio en cada recurso (`mean`, `max`). |
| `dpc_isr_top_drivers` | Los 5 drivers con más tiempo de DPC/ISR (`kind`, `module`, `count`, `count_over_1ms`, `max_usecs_bucket`, `approx_total_usecs`). |
| `top_net_processes` | Los 5 procesos con más tráfico de red promedio. |
| `largest_private_bytes_growth` | El proceso que más creció en private bytes durante la Ventana. |
