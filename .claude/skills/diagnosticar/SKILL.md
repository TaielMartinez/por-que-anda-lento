---
name: diagnosticar
description: Diagnosticar por qué esta PC Windows anda lenta (se traba, el mouse salta, la RAM figura alta, tirones). Conduce una Consulta completa: pregunta los Síntomas, toma una Captura con el Colector y escribe un Diagnóstico con evidencia.
---

# Diagnosticar

Conducís una **Consulta**: Síntomas → Captura → Diagnóstico. El vocabulario está en `CONTEXT.md`: usá sus términos.

Sos de **solo lectura**. Nunca modificás el sistema: no matás procesos, no cambiás servicios ni drivers ni configuración. Las correcciones las aplica el usuario a partir de tus recomendaciones. La única excepción es la Preparación (`uv run setup`), y solo con el permiso explícito del usuario.

## 1. Síntomas

1. Pedile al usuario que cuente con sus palabras qué nota.
2. Completá con la checklist lo que el relato no haya cubierto. Preguntá todo junto, en una sola tanda:
   - ¿Está lenta **ahora mismo**?
   - ¿Desde cuándo pasa? ¿Cambió algo en ese momento (hardware, drivers, software, una actualización)?
   - ¿Con qué frecuencia? ¿Cuánto dura cada episodio?
   - ¿Aparece después de horas encendida, al volver de suspensión, o desde el arranque?
   - ¿Qué estaba haciendo (juego, navegador, trabajo, nada)?
   - ¿Qué se traba: el mouse, el audio, el video, todo el sistema, una sola app?
   - ¿Se arregla solo, cerrando algo, o solo reiniciando?
3. Creá `consultations/<AAAA-MM-DD_HHMMSS>/` con la fecha y hora actuales y escribí ahí `symptoms.md`: el relato textual y cada respuesta de la checklist ("no sabe" también es una respuesta).

**Listo cuando:** `symptoms.md` existe y tiene una respuesta para cada punto de la checklist.

## 2. Captura

Elegí los argumentos según los Síntomas:

| Situación | Comando |
|---|---|
| No está lenta ahora | `uv run collect --reference` (queda como Referencia) |
| Está lenta ahora, de forma sostenida | `uv run collect` (60 s) |
| Está lenta ahora, pero con tirones cortos y esporádicos | `uv run collect --duration 180` |

Avisale al usuario que va a aparecer un pedido de UAC y que tiene que aceptarlo. Ejecutá el comando con un timeout de la duración más 5 minutos. La última línea de la salida es la ruta de la Captura. Si el comando sale con código 2, el usuario rechazó el UAC: preguntale si quiere reintentar.

Leé `summary.json` y `manifest.json`. Si `missing_tools` no está vacío, decile qué datos faltan por eso (`needed_for`) y ofrecele la Preparación. Mostrale `uv run setup --status`. Solo si acepta de forma explícita (instala herramientas y el driver PawnIO, y acepta sus licencias), corré `uv run setup --yes` y repetí la Captura.

**Listo cuando:** tenés la ruta de una Captura y leíste su Resumen y su manifest.

## 3. Referencia

Buscá la Referencia vigente: el `captures/*/manifest.json` más reciente con `"is_reference": true`, excluyendo la Captura recién tomada. Si existe, usala para comparar los mismos archivos en ambas Capturas.

Escribí `captures.json` en la carpeta de la Consulta:

```json
{"capture": "captures/<id>", "reference": "captures/<id>" }
```

Usá `"reference": null` si no hay Referencia.

## 4. Investigación

Partí de los Síntomas. Para cada uno, abrí solo los archivos que lo pueden explicar. El manifest dice qué pregunta responde cada archivo, y `docs/capture/<dominio>.md` explica cómo interpretar sus campos. Leé el documento del dominio antes de sacar conclusiones de un campo que no conocés.

Puntos de entrada por Síntoma:

- **El mouse salta, tirones, audio que se corta**: `sampling/` (% DPC, % interrupciones, DPC/ISR por driver), temperaturas, `processes_top_cpu`.
- **La RAM figura alta o "no aparece"**: `snapshot/memory/attribution`, `pool_tags`, `processes_top_ram` (el delta muestra fugas), `snapshot/processes/handles`.
- **El disco al 100 %, todo tarda en abrir**: cola de disco y hard page faults en `sampling/`, `processes_top_disk`, `snapshot/storage/`.
- **Empeora con las horas**: `uptime_hours`, crecimiento en `processes_top_ram`, pool no paginado, Historial.
- **Juegos o video**: `gpu`, temperaturas, `graphics_settings`, eventos TDR en el Historial.
- **Siempre**: `snapshot/system/` (configuración de la RAM, BIOS, plan de energía) y el Historial (WHEA, errores de disco).

Por cada hipótesis buscá también la evidencia **en contra**. Si hay Referencia, compará: un valor alto solo importa si es distinto de cuando la PC anda bien.

**Listo cuando:** cada Síntoma tiene al menos una hipótesis con evidencia a favor o en contra, o está marcado como no explicable con estos datos.

## 5. Diagnóstico

Escribí `diagnosis.md` en la carpeta de la Consulta con esta estructura:

```markdown
# Diagnóstico

## Resumen
Dos o tres oraciones: qué explica la lentitud, con qué confianza.

## Hipótesis
### 1. <causa> (probabilidad: alta | media | baja)
- Evidencia: `<archivo>`: <campo> = <valor> (Referencia: <valor> si hay)
- Explica los Síntomas: ...
- En contra: ...

## Descartado
- <causa>: por qué, con el archivo y el valor.

## Recomendaciones
Pasos concretos que aplica el usuario, ordenados por impacto y facilidad.

## Próxima Captura
Solo si los datos no alcanzan: cuándo tomarla (por ejemplo, "durante un episodio") y con qué argumentos.
```

**Listo cuando:** cada hipótesis cita archivo y valor, y cada Síntoma de `symptoms.md` aparece en una hipótesis, en Descartado o en Próxima Captura.

Por último, contale al usuario el Resumen y las recomendaciones principales en el chat, y dale la ruta de `diagnosis.md`.
