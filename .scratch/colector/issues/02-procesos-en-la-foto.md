# 02: Procesos en la Foto

**What to build:** La Captura incluye el dominio `processes`, partido en archivos que responden una sola pregunta: lista de procesos (CPU, private bytes, working set, handles, threads), árbol padre-hijo, líneas de comando completas sin filtrar (ADR 0001), I/O acumulado y handles. El agente puede saber qué corre y para qué se usa la PC abriendo solo el archivo que necesita.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Archivos separados para lista, árbol, líneas de comando, I/O y handles, cada uno con su entrada en el manifest.
- [ ] Procesos protegidos o que terminan durante la lectura no rompen el dominio; el manifest marca `partial` con motivo si faltan datos.
- [ ] Líneas de comando sin enmascarar.
- [ ] Resumen: cantidad de procesos, suma de private bytes y de working set.
- [ ] Tests con fixtures grabadas de esta PC a través de los puertos.
- [ ] Documento del dominio `processes`.
