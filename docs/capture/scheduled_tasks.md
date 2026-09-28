# Dominio `scheduled_tasks`

Parte de la **Foto**. Carpeta: `snapshot/scheduled_tasks/`. Tareas programadas habilitadas: pueden disparar trabajo pesado a intervalos, como indexado, desfragmentación, telemetría o actualizadores. Eso explica una lentitud que "aparece cada tanto".

Campos de cada tarea:
- `full_path`, `path`, `name`.
- `state`: `Ready` o `Running`.
- `author`.
- `actions`: qué ejecuta.
- `triggers`: clases de disparador, como `MSFT_TaskLogonTrigger`, `MSFT_TaskDailyTrigger`, `MSFT_TaskIdleTrigger` o `MSFT_TaskBootTrigger`.
- `last_run`, `next_run`.
- `last_result`: 0 = OK. Por ejemplo, 267009 significa que está corriendo.

## Archivos

### `enabled`: ¿Qué tareas programadas están habilitadas, qué ejecutan y cuándo corrieron?

Todas las tareas que no están deshabilitadas, ordenadas por ruta.

### `third_party`: ¿Qué tareas programadas habilitadas no son de Windows?

Las que no están bajo `\Microsoft\`.

## Sección del Resumen (`summary.scheduled_tasks`)

| Campo | Qué es |
|---|---|
| `enabled_count` | Tareas habilitadas. |
| `third_party` | Rutas de las tareas de terceros. |
| `running` | Tareas corriendo en el momento de la Captura. |
| `ran_last_hour` | Tareas que corrieron en la hora previa a la Captura: cruzar con el horario del Síntoma. |
