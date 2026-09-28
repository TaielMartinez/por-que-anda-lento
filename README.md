# Por qué anda lento

Herramienta para diagnosticar por qué una PC Windows anda lenta. Un **Colector** en Python observa todo lo que se puede observar del sistema y lo guarda como una **Captura**, partida en archivos chicos. Después un agente cruza la Captura con los **Síntomas** que describe el usuario y escribe un **Diagnóstico**.

- Vocabulario: [CONTEXT.md](CONTEXT.md)
- Qué se recopila, dónde y con qué estructura: [docs/capture/README.md](docs/capture/README.md)
- Decisiones: [docs/adr/](docs/adr/)

## Requisitos

- Windows 10 u 11, Python 3.12 o superior y [uv](https://docs.astral.sh/uv/).
- Permisos de administrador: el Colector los pide solo, por UAC.

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
