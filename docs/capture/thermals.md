# Dominio `thermals`

Parte de la **Foto**. Carpeta: `snapshot/thermals/`. Sensores de hardware leídos con LibreHardwareMonitor (lo instala la Preparación). Sirve para detectar **thermal throttling**: la CPU o la GPU bajan su frecuencia al calentarse y todo se vuelve lento o a tirones.

Si LibreHardwareMonitor no está instalado, el dominio queda `failed` y el resto de la Captura se genera igual. Para leer la CPU y la placa necesita además el driver PawnIO y admin. Sin eso, esos sensores aparecen con `value: null` y los archivos quedan `partial`. La GPU y los discos se leen igual.

Campos de cada sensor:
- `hardware`, `hardware_type` (`Cpu`, `GpuNvidia`, `Motherboard`, `SuperIO`, `Storage`, `Memory`...), `parent`.
- `sensor`, `type`, `unit`.
- `value`, y `min` y `max` desde que se abrió el lector.

## Archivos

### `all_sensors`: ¿Qué valor tiene cada sensor de hardware (todos los tipos)?

Todos los sensores, incluidos carga (`Load`), voltajes y datos.

### `temperatures`: ¿A qué temperatura están la CPU, la GPU, la placa y los discos?

Referencias:
- **CPU**: más de 90 °C bajo carga, o más de 60 °C en reposo, indica mala refrigeración (pasta térmica, disipador, ventiladores). "Distance to TjMax" es cuánto falta para el límite: cerca de 0 significa throttling.
- **GPU**: más de 83 °C en el núcleo, o más de 100 °C en "Hot Spot" o "Memory Junction", la hace bajar clocks.
- **NVMe**: más de 70 °C la hace bajar la velocidad.

### `clocks`: ¿A qué frecuencia corren los núcleos de la CPU, la GPU y la memoria?

Si los núcleos de la CPU están muy por debajo de su frecuencia máxima (`max_clock_mhz` en `snapshot/system/hardware`) **bajo carga**, hay throttling térmico o de energía, o un plan de energía restrictivo. En reposo es normal que bajen.

### `fans`: ¿A qué velocidad giran los ventiladores?

Tipos `Fan` (RPM) y `Control` (% de la curva). 0 RPM con temperaturas altas indica un ventilador detenido o desconectado. En GPUs, 0 RPM en reposo es normal (modo pasivo).

### `power`: ¿Cuánta potencia consumen la CPU y la GPU?

En W. Una CPU que no pasa de unos pocos W bajo carga puede estar limitada por el BIOS o por el plan de energía.

## Sección del Resumen (`summary.thermals`)

| Campo | Qué es |
|---|---|
| `max_temperature_c_by_hardware` | Temperatura máxima actual por componente (sin contar "Distance to TjMax"). |
| `cpu_package_c` | Temperatura del paquete de la CPU. |
| `cpu_average_clock_mhz` | Promedio de la frecuencia de los núcleos. |
| `sensors_without_value` | Sensores sin lectura (CPU y placa sin PawnIO o sin admin). |
