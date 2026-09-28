# Dominio `startup`

Parte de la **Foto**. Carpeta: `snapshot/startup/`. Lo que se ejecuta solo al arrancar Windows o al iniciar sesión.

## Archivos

### `entries`: ¿Qué programas se ejecutan al arrancar Windows o al iniciar sesión?

Con la Preparación hecha, la fuente es Sysinternals Autoruns (`source: "autoruns"`), que cubre claves Run, carpetas de Inicio, Winlogon y boot execute, y verifica firmas. Campos:
- `entry`, `location`, `enabled`, `category`, `profile` (usuario o `System-wide`).
- `description`, `company`, `image_path`, `version`.
- `signer`: `(Verified) ...` si la firma es válida, `(Not Verified) ...` si no.
- `launch_string`: la línea completa que se ejecuta.
- `registered_at`: cuándo se modificó la entrada.

Sin Autoruns, la fuente son solo las claves `Run`/`RunOnce` del registro (`source: "registry"`), con `enabled: null` porque no se sabe si están deshabilitadas en el Administrador de tareas. El archivo queda `partial`.

**Cómo interpretarlo.** Cada entrada habilitada es un proceso que queda residente. Las utilidades de fabricantes (RGB, placa, periféricos) y los "actualizadores" son sospechosos frecuentes de consumo en segundo plano y de latencia DPC.

## Sección del Resumen (`summary.startup`)

| Campo | Qué es |
|---|---|
| `count`, `enabled_count` | Entradas totales y habilitadas. |
| `not_verified` | Entradas habilitadas con firma no verificada. |
