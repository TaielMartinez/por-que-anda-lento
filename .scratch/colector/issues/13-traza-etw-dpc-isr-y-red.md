# 13: Traza ETW: DPC/ISR y red por proceso

**What to build:** Durante la Ventana de muestreo se graba una traza ETW con WPR y se procesa con xperf para obtener la latencia DPC/ISR por driver y el tráfico de red por proceso, para explicar el mouse que "salta". Salen `dpc_isr_by_driver` y el top 20 de procesos por red, en archivos separados; el `.etl` se borra salvo `--keep-etl`.

**Blocked by:** 05, 08

**Status:** ready-for-agent

- [ ] La traza cubre exactamente la Ventana de muestreo.
- [ ] DPC/ISR por driver: cantidad, tiempo total, máximo e histograma de duración.
- [ ] Top 20 de procesos por red (bytes enviados + recibidos) en archivo separado.
- [ ] El `.etl` se borra salvo `--keep-etl`; el manifest indica si se conservó.
- [ ] Sin WPT, estos archivos quedan `failed` con motivo y el resto de la Ventana de muestreo se genera.
- [ ] Resumen: driver con mayor latencia DPC/ISR y proceso con más tráfico.
- [ ] Tests con fixtures de salidas de xperf.
- [ ] Documento de la Ventana de muestreo actualizado.
