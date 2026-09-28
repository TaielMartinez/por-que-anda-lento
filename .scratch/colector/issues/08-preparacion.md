# 08: Preparación

**What to build:** El usuario ejecuta el comando de Preparación una vez (con admin) y queda todo listo: se descargan LibreHardwareMonitor, Sysinternals (autorunsc, sigcheck, handle) y pooltag.txt, con versión fijada y SHA256 verificado, desde sus fuentes oficiales, a una carpeta ignorada por git; y se instala Windows Performance Toolkit desde el ADK. Si después falta alguna, el Colector lo registra en el manifest sin instalar nada (ADR 0003).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Manifiesto de herramientas con versión, URL oficial y SHA256.
- [ ] Si el hash no coincide, la herramienta no se instala y se informa el error.
- [ ] Idempotente: una segunda ejecución no vuelve a descargar lo que ya está verificado.
- [ ] Instala solo el componente WPT del ADK, en modo silencioso.
- [ ] El Colector detecta las herramientas faltantes y las lista en el manifest.
- [ ] Tests del chequeo de herramientas faltantes vía puertos; descarga e instalación verificadas a mano con checklist.
- [ ] README con cómo correr la Preparación.
