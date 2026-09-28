# Dominio `windows`

Parte de la **Foto**. Carpeta: `snapshot/windows/`. Qué estaba haciendo el usuario: la ventana con el foco y las ventanas abiertas. Los títulos van **sin filtrar** (ADR 0001): pueden incluir nombres de archivos, pestañas del navegador o conversaciones.

Campos de cada ventana: `pid`, `process_name`, `title`, `foreground` (tiene el foco), `minimized`.

## Archivos

### `foreground`: ¿Qué ventana tenía el foco en el momento de la Captura?

La ventana activa, o `null` si no había ninguna (por ejemplo, con el escritorio seleccionado). Cuando la Captura se toma desde el agente, normalmente es la terminal o el editor.

### `visible`: ¿Qué ventanas estaban abiertas y visibles, de qué proceso y con qué título?

Todas las ventanas visibles con título, incluidas las minimizadas (`minimized: true`).

## Sección del Resumen (`summary.windows`)

| Campo | Qué es |
|---|---|
| `foreground_process`, `foreground_title` | La ventana activa. |
| `visible_count` | Cantidad de ventanas visibles. |
