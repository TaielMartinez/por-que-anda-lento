# 08: Preparación

**What to build:** El usuario ejecuta el comando de Preparación una vez (con admin) y queda todo listo: se descargan LibreHardwareMonitor, Sysinternals (autorunsc, sigcheck, handle) y pooltag.txt, con versión fijada y SHA256 verificado, desde sus fuentes oficiales, a una carpeta ignorada por git; y se instala Windows Performance Toolkit desde el ADK. Si después falta alguna, el Colector lo registra en el manifest sin instalar nada (ADR 0003).

**Blocked by:** 01

**Status:** ready-for-agent

- [x] Manifiesto de herramientas con versión, URL oficial y SHA256.
- [x] Si el hash no coincide, la herramienta no se instala y se informa el error.
- [x] Idempotente: una segunda ejecución no vuelve a descargar lo que ya está verificado.
- [x] Instala solo el componente WPT del ADK, en modo silencioso.
- [x] El Colector detecta las herramientas faltantes y las lista en el manifest.
- [x] Tests del chequeo de herramientas faltantes vía puertos; descarga e instalación verificadas a mano con checklist.
- [x] README con cómo correr la Preparación.

## Comments

Verificación manual pendiente (necesita admin y aceptar licencias):
- [ ] `uv run setup` pide confirmación, pide UAC e instala las 7 herramientas.
- [ ] Una segunda ejecución informa "ya estaba" para todas.
- [ ] `uv run setup --status` muestra todo OK.
- [ ] Alterar un byte de un archivo en `tools/_downloads/` y borrar la herramienta: la Preparación la vuelve a bajar.
