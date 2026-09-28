# 01: Captura mínima de punta a punta

**What to build:** El usuario ejecuta un único comando del Colector; aparece el pedido de UAC, acepta, y al terminar el comando imprime la ruta de una Captura nueva que contiene el manifest, el Resumen y el dominio `system` (hardware, OS, uptime, plan de energía, Game Mode, HAGS). Establece la base del proyecto: uv, los puertos de lectura hacia Windows, la base de tests con fixtures grabadas, el índice de la documentación de la Captura y la prueba de humo real. Ver spec y ADRs 0001–0003.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Proyecto gestionado con uv; el Colector se ejecuta con un único comando.
- [ ] Sin admin, el Colector se auto-eleva por UAC; el proceso original espera y emite la ruta de la Captura. Si el usuario rechaza el UAC, termina con un mensaje claro y código de error.
- [ ] Cada ejecución crea una carpeta de Captura identificada por fecha y hora, en un directorio ignorado por git.
- [ ] `manifest.json` incluye versión de esquema, inicio/fin y una entrada por archivo con la pregunta que responde, tamaño y estado (`complete`/`partial`/`failed` + motivo).
- [ ] Un dominio que lanza una excepción queda `failed` en el manifest y no aborta la Captura.
- [ ] `summary.json` existe (con los campos que aporte `system`).
- [ ] Dominio `system` escrito en archivos de una sola pregunta.
- [ ] Todo acceso a Windows pasa por los puertos de lectura cruda; los tests ejecutan el Colector completo con fixtures grabadas de esta PC y verifican solo la Captura resultante.
- [ ] Prueba de humo real marcada aparte (no corre por defecto) que ejecuta el Colector con admin y valida la Captura contra el esquema.
- [ ] Documentación: índice de la Captura (estructura, manifest, Resumen, cómo navegar) + documento del dominio `system`.
- [ ] Verificación manual: UAC aceptado y rechazado.
