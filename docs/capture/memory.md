# Dominio `memory`

Parte de la **Foto**. Carpeta: `snapshot/memory/`. Responde la pregunta "el Administrador de tareas dice 80 % pero los procesos suman mucho menos: ¿a dónde se va la RAM?".

## Conceptos

- **Usada** = total − disponible. **Disponible** = standby + libre + cero: memoria que Windows puede entregar de inmediato.
- **Standby**: caché de archivos y páginas recientes. Es reutilizable, así que no es un problema aunque sea grande.
- **Modificada**: páginas que deben escribirse a disco antes de poder reutilizarse. Cuenta como usada.
- **Working set privado** de un proceso: su memoria física no compartida. Es lo que suma el Administrador de tareas en la columna "Memoria".
- **Pool no paginado**: memoria del kernel y los drivers que nunca va a disco. Una fuga de un driver lo hace crecer sin que ningún proceso lo muestre.
- **Almacén de compresión** (proceso "Memory Compression"): páginas comprimidas en RAM en lugar de ir al archivo de paginación.

## Archivos

### `totals`: ¿Cuánta RAM y memoria comprometida se usa en total?

| Campo | Qué es |
|---|---|
| `physical_total_bytes`, `physical_available_bytes`, `physical_used_bytes` | RAM total, disponible y usada. |
| `commit_total_bytes`, `commit_limit_bytes`, `commit_peak_bytes` | Memoria comprometida (RAM + archivo de paginación). Si el total se acerca al límite, las apps fallan al pedir memoria aunque haya RAM "libre". |
| `cache_bytes` | Caché del sistema de archivos residente. |
| `paged_pool_bytes`, `nonpaged_pool_bytes` | Pool del kernel (el paginado puede estar parcialmente en disco). |
| `handle_count`, `process_count`, `thread_count` | Totales del sistema. |

### `page_lists`: ¿Cuánta RAM está en standby (caché reutilizable), modificada o libre?

- `standby_bytes`: el total de standby, con su detalle por prioridad en `standby` (`core_bytes`, `normal_priority_bytes`, `reserve_bytes`).
- `modified_bytes`: páginas modificadas pendientes de escribir.
- `free_and_zero_bytes`: memoria sin usar.

### `compression`: ¿Cuánta RAM ocupa el almacén de memoria comprimida?

`compression_store_bytes`: working set del proceso Memory Compression. Si es grande, el sistema estuvo bajo presión de memoria y comprimió en lugar de paginar.

### `pool_tags`: ¿Qué tags del pool del kernel ocupan más memoria?

Cada asignación del pool lleva un tag de 4 letras que identifica al driver o componente que la hizo. Ordenado por `nonpaged_bytes`. Campos: `tag`, `nonpaged_bytes`, `paged_bytes`, `nonpaged_outstanding_allocs`, `paged_outstanding_allocs` (asignaciones sin liberar). Si hay cientos de miles de asignaciones pendientes y creciendo, es señal de fuga.

Tags frecuentes: `NVRM` (driver NVIDIA), `EtwB` (buffers de ETW), `smNp` y `smCB` (gestor de memoria y compresión), `File` (objetos de archivo), `Ntfx`/`NtFs` (NTFS). La traducción de cada tag a su driver está en el ticket de mapeo (pooltag).

### `attribution`: ¿Cuánta RAM usada no se atribuye a ningún proceso y en qué se descompone?

| Campo | Qué es |
|---|---|
| `used_bytes` | RAM usada (total − disponible). |
| `processes_private_working_set_bytes` | Suma de los working sets privados de todos los procesos, sin contar Memory Compression. Es lo que "suma" el Administrador de tareas. Incluye VMs como `vmmemWSL`. |
| `unattributed_to_processes_bytes` | `used_bytes − processes_private_working_set_bytes`: la RAM que "no aparece". |
| `breakdown` | En qué se va la parte no atribuida. |

Componentes de `breakdown`:

| Campo | Qué es |
|---|---|
| `nonpaged_pool_bytes` | Pool no paginado (kernel y drivers). |
| `paged_pool_resident_bytes` | Parte del pool paginado que está en RAM. |
| `system_cache_resident_bytes` | Caché de archivos del sistema en RAM. |
| `system_driver_resident_bytes` | Código de drivers en RAM. |
| `system_code_resident_bytes` | Código del kernel en RAM. |
| `compression_store_bytes` | Almacén de compresión. |
| `modified_page_list_bytes` | Páginas modificadas. |
| `unexplained_bytes` | Lo que queda: memoria compartida entre procesos (DLLs, archivos mapeados), tablas de páginas, memoria bloqueada por drivers (AWE, GPU), memoria reservada por el hipervisor. Un valor de varios GB justifica investigar drivers de GPU, VMs o software que bloquea memoria. |

## Sección del Resumen (`summary.memory`)

| Campo | Qué es |
|---|---|
| `total_bytes`, `used_bytes`, `available_bytes`, `used_percent` | Uso de RAM. |
| `commit_percent` | Memoria comprometida sobre el límite. |
| `standby_bytes` | Standby total. |
| `processes_private_working_set_bytes` | Lo atribuido a procesos. |
| `unattributed_to_processes_bytes`, `unattributed_breakdown` | La RAM que no aparece y su descomposición (igual que `attribution`). |
| `top_nonpaged_pool_tags` | Los 5 tags con más pool no paginado. |
