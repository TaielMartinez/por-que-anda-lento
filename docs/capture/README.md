# La Captura

Una **Captura** es todo lo que el Colector observó en una ejecución: una **Foto** (estado en un instante), una **Ventana de muestreo** (series temporales durante N segundos) y un **Historial** (eventos de los últimos días), más un **Resumen** con métricas derivadas. Vocabulario completo en [CONTEXT.md](../../CONTEXT.md).

Está partida en muchos archivos chicos, cada uno responde **una sola pregunta**. La idea es no leerla entera: empezar por el Resumen y el manifest, y abrir solo lo relacionado con el Síntoma.

## Cómo generarla

```bash
uv run collect                 # Ventana de muestreo de 60 s, una muestra por segundo
uv run collect --duration 300  # síntoma esporádico: muestrear más tiempo
uv run collect --reference     # la PC anda bien ahora: guardar como Referencia
```

El Colector pide admin por UAC (ADR 0002) e imprime la ruta de la Captura al terminar. Nunca modifica el sistema. Las herramientas externas se instalan aparte con `uv run setup` (la Preparación, ADR 0003).

## Dónde queda

```
captures/<AAAA-MM-DD_HHMMSS>/
  manifest.json     índice: qué archivo responde qué pregunta, tamaño y estado
  summary.json      el Resumen: números derivados, sin veredictos
  snapshot/<dominio>/*.json   la Foto, un subdirectorio por dominio
  sampling/*.csv              la Ventana de muestreo, un CSV por métrica
  history/*.json              el Historial, un archivo por fuente de eventos
  raw/                        salidas crudas de herramientas externas
```

Las Capturas no se borran solas. Los datos se guardan **sin filtrar** (líneas de comando, títulos de ventana; ADR 0001).

## Cómo leerla (para agentes)

1. **`summary.json`**: primera lectura, barata. Tiene una sección por dominio.
2. **`manifest.json`**: elegir qué abrir según la pregunta de cada archivo.
3. El archivo puntual y, si hace falta interpretar campos, el documento de su dominio (abajo).
4. Si hay una Referencia, comparar el mismo archivo en ambas Capturas.

### `manifest.json`

| Campo | Qué es |
|---|---|
| `schema_version` | Versión del formato de la Captura (hoy `1`). |
| `capture_id` | Nombre de la carpeta. |
| `started_at` / `finished_at` | Inicio y fin, ISO 8601 con zona horaria. |
| `is_reference` | `true` si se tomó con la PC andando bien (Referencia). |
| `sampling` | `duration_s` e `interval_s` de la Ventana de muestreo. |
| `missing_tools` | Herramientas de la Preparación que faltaban (los datos que dependen de ellas quedan `partial`/`failed`). |
| `domains.<nombre>` | `status` (`complete` / `partial` / `failed`) y `reasons` (por qué no está completo). |
| `files[]` | Un elemento por archivo: `path`, `domain`, `question` (la pregunta que responde), `bytes`, `status`, `reason`. |
| `errors` | Traza de la excepción de cada dominio que falló (para depurar el Colector). |

Estados:
- `complete`: se leyó todo lo previsto.
- `partial`: el archivo existe pero le falta algo; `reason` dice qué.
- `failed`: el dominio no pudo generar sus archivos; mirar `domains.<nombre>.reasons`.

### `summary.json`

Un objeto con una sección por dominio. Cada documento de dominio describe su sección. Son números para orientarse, no conclusiones: el Diagnóstico lo hace el agente cruzándolos con los Síntomas.

## Dominios

| Documento | Parte | Qué responde |
|---|---|---|
| [system.md](system.md) | Foto | Hardware, Windows, uptime, energía, Game Mode, HAGS |
| [processes.md](processes.md) | Foto | Procesos: memoria, CPU, árbol, líneas de comando, I/O, handles |
| [memory.md](memory.md) | Foto | RAM usada, standby, compresión, pool del kernel, RAM no atribuida a procesos |
| [storage.md](storage.md) | Foto | Espacio libre, discos físicos, salud y SMART |
| [devices.md](devices.md) | Foto | Dispositivos PnP, USB/HID y dispositivos con error |
| [network.md](network.md) | Foto | Adaptadores, IP y conexiones abiertas por proceso |
| [windows.md](windows.md) | Foto | Ventana activa y ventanas visibles (qué hace el usuario) |
| [software.md](software.md) | Foto | Programas instalados e instalaciones recientes |
| [sampling.md](sampling.md) | Ventana de muestreo | CPU por núcleo, DPC/interrupciones, disco, hard page faults, memoria y tops de procesos por recurso |
| [history.md](history.md) | Historial | Errores de disco, WHEA, falta de memoria, arranques lentos, TDR de GPU, apagados inesperados, cierres de apps (7 días) |

## Unidades y convenciones

- Tamaños en **bytes** (campos `*_bytes`), salvo que el nombre diga otra unidad (`*_mb`, `*_kb`).
- Tiempos en ISO 8601 con zona horaria; duraciones con la unidad en el nombre (`*_s`, `*_hours`).
- `null` significa "no se pudo leer" o "Windows no lo informa"; nunca cero.
