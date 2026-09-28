# Por qué anda lento

Herramienta para diagnosticar por qué una PC Windows anda lenta. Un **Colector** en Python observa todo lo que se puede observar del sistema y lo guarda como una **Captura**, partida en archivos chicos. Después un agente cruza la Captura con los **Síntomas** que describe el usuario y escribe un **Diagnóstico**.

- Vocabulario: [CONTEXT.md](CONTEXT.md)
- Qué se recopila, dónde y con qué estructura: [docs/capture/README.md](docs/capture/README.md)
- Decisiones: [docs/adr/](docs/adr/)

## Requisitos

- Windows 10 u 11, Python 3.12 o superior y [uv](https://docs.astral.sh/uv/).
- Permisos de administrador: el Colector los pide solo, por UAC.

## Preparación

`uv run setup` descarga desde las fuentes oficiales, verifica por SHA256 e instala:

| Herramienta | Para qué |
|---|---|
| LibreHardwareMonitor 0.9.6 + driver PawnIO 2.2.0 | temperaturas, ventiladores y clocks |
| Sysinternals Autoruns, Sigcheck, Handle | programas de inicio, firmas de drivers, handles |
| Windows Performance Toolkit (ADK 10.1.26100.9457) | latencia DPC/ISR por driver y red por proceso |
| Debugging Tools (SDK 10.0.26100.9169) | `pooltag.txt`, para traducir tags del pool a drivers |

Pide confirmación porque instalar implica aceptar sus licencias (o `--yes`), y pide admin por UAC. Es idempotente: lo instalado se saltea. `uv run setup --status` muestra qué falta. Las versiones y hashes están fijados en `src/lento/tools.py`. Si una fuente publica otra versión, la verificación falla y hay que actualizarlos a mano (ADR 0003).

## Uso

```bash
uv run setup      # Preparación: descarga e instala las herramientas externas (una vez)
uv run collect    # toma una Captura e imprime su ruta
```

Con Claude Code, `/diagnosticar` conduce el proceso completo: pregunta los Síntomas, toma la Captura y escribe el Diagnóstico.

## Desarrollo

```bash
uv run pytest               # tests contra fixtures grabadas (no necesitan admin)
uv run pytest -m smoke      # prueba de humo con el Colector real (terminal como admin)
uv run mypy                 # chequeo de tipos
uv run record-fixture <nombre> --domains <d1,d2>   # grabar un fixture nuevo desde esta PC
```

Todo acceso a Windows pasa por los puertos (`lento.ports.Ports`). Los tests ejecutan el Colector completo con `FixturePorts` y verifican solo la Captura resultante.
