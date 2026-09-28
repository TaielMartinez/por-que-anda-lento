# Dominio `processes`

Parte de la **Foto**. Carpeta: `snapshot/processes/`. Qué está corriendo en el momento de la Captura. Los valores son acumulados desde que arrancó cada proceso: para ver tasas (CPU %, MB/s) usar la Ventana de muestreo.

Los datos van **sin filtrar**: las líneas de comando pueden tener tokens o rutas personales (ADR 0001).

## Archivos

### `list`: ¿Qué procesos corren y cuánta memoria, CPU, hilos y handles usa cada uno?

Ordenado por `private_bytes` de mayor a menor. Campos:

| Campo | Qué es |
|---|---|
| `pid`, `ppid` | Id del proceso y de su padre. |
| `name`, `username`, `status`, `priority` | Identificación y prioridad base (32 = normal, 128 = alta, 64 = inactiva). |
| `started_at` | Cuándo arrancó. |
| `cpu_s` | Segundos de CPU acumulados (usuario + kernel). |
| `private_bytes` | Memoria comprometida privada (lo que el proceso reservó para sí; incluye lo paginado a disco). Es la mejor señal de una fuga en un proceso. |
| `working_set_bytes` | Memoria física que ocupa ahora, incluida la compartida. Sumar working sets sobrecuenta. |
| `peak_working_set_bytes` | Máximo histórico del working set. |
| `paged_pool_bytes`, `nonpaged_pool_bytes` | Pool del kernel cargado a este proceso (casi siempre chico). |
| `num_threads`, `num_handles` | Hilos y handles abiertos. |

`null` en `private_bytes` y similares significa que no se pudo abrir el proceso (protegido, o terminó durante la lectura). En ese caso el archivo queda `partial`.

### `tree`: ¿Qué proceso lanzó a cuál (árbol padre-hijo)?

Lista de raíces. Cada nodo tiene `pid`, `name` y `children`. Si un padre ya no existe, o su PID fue reutilizado por otro proceso más nuevo, el hijo aparece como raíz.

### `cmdlines`: ¿Con qué línea de comando y ejecutable se lanzó cada proceso?

`pid`, `name`, `exe` (ruta completa), `cmdline` (texto completo). Sirve para distinguir instancias del mismo programa, como las pestañas de Chrome o varios `svchost.exe`, y para ver para qué se está usando la PC.

### `io`: ¿Cuánto leyó y escribió cada proceso desde que arrancó?

Ordenado por lectura + escritura. Tiene `io_read_bytes`, `io_write_bytes` e `io_other_bytes` (operaciones que no son de lectura ni escritura, por ejemplo control de dispositivos), más `io_read_count` e `io_write_count`. Incluye disco, red y dispositivos: Windows no los separa por proceso.

### `handles`: ¿Qué procesos tienen más handles e hilos abiertos (posibles fugas)?

Ordenado por `num_handles`. Como referencia, un proceso normal tiene cientos o pocos miles de handles. Decenas de miles, y creciendo, suele indicar una fuga.

## Sección del Resumen (`summary.processes`)

| Campo | Qué es |
|---|---|
| `count` | Procesos en ejecución. |
| `private_bytes_total` | Suma de `private_bytes`. |
| `working_set_bytes_total` | Suma de working sets (sobrecuenta la memoria compartida). |
| `threads_total`, `handles_total` | Totales del sistema. |
| `inaccessible_count` | Procesos que no se pudieron leer. |
