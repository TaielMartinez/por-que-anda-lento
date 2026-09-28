# 09: Qué corre y qué arranca

**What to build:** La Captura incluye los dominios `services`, `startup` (vía autorunsc), `scheduled_tasks`, `drivers` (versión, fecha, firma vía sigcheck), `security` (Defender: escaneos activos, exclusiones) y `updates` (Windows Update en curso), para que el agente detecte carga innecesaria, drivers viejos o sin firmar, y lentitud transitoria por escaneos o actualizaciones.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] Cada dominio en archivos de una sola pregunta.
- [ ] Sin Sysinternals, `startup` y `drivers` quedan `partial` con lo que se pueda leer sin ellas y el motivo en el manifest.
- [ ] Resumen: servicios en ejecución, entradas de inicio, drivers sin firmar, si hay escaneo o update en curso.
- [ ] Tests con fixtures de salidas de autorunsc y sigcheck.
- [ ] Un documento por dominio.
