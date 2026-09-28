# 05: Ventana de muestreo base

**What to build:** La Captura incluye una Ventana de muestreo de duración e intervalo configurables (por defecto 60 s, cada 1 s) con series temporales, un CSV por métrica: CPU por núcleo, % DPC time, % interrupt time, cola de disco, hard page faults y memoria disponible. Además, `processes_all` (todos los procesos en cada muestra) y un top 20 por recurso en archivos separados para CPU, RAM (con delta de private bytes desde el inicio) y disco.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Duración e intervalo configurables por argumento; valores por defecto 60 s / 1 s.
- [ ] Un CSV por métrica de sistema, con timestamp.
- [ ] `processes_all` + tops de CPU, RAM (con `private_bytes_delta`) y disco en archivos separados; el manifest explica el criterio de cada top.
- [ ] Resumen: picos, promedios y percentiles de cada métrica.
- [ ] Tests con secuencias de muestras grabadas (puertos de contadores y procesos falsos, reloj controlado).
- [ ] Documento de la Ventana de muestreo.
