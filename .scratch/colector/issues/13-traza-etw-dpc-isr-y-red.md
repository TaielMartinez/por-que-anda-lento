# 13: Traza ETW: DPC/ISR y red por proceso

**What to build:** Durante la Ventana de muestreo se graba una traza ETW con WPR y se procesa con xperf para obtener la latencia DPC/ISR por driver y el tráfico de red por proceso, para explicar el mouse que "salta". Salen `dpc_isr_by_driver` y el top 20 de procesos por red, en archivos separados; el `.etl` se borra salvo `--keep-etl`.

**Blocked by:** 05, 08

**Status:** ready-for-agent

- [x] La traza cubre exactamente la Ventana de muestreo.
- [x] DPC/ISR por driver: cantidad, tiempo total, máximo e histograma de duración.
- [x] Top 20 de procesos por red (bytes enviados + recibidos) en archivo separado.
- [x] El `.etl` se borra salvo `--keep-etl`; el manifest indica si se conservó.
- [x] Sin WPT, estos archivos quedan `failed` con motivo y el resto de la Ventana de muestreo se genera.
- [x] Resumen: driver con mayor latencia DPC/ISR y proceso con más tráfico.
- [x] Tests con fixtures de salidas de xperf.
- [x] Documento de la Ventana de muestreo actualizado.

## Comments

Los parsers de `xperf -a dpcisr` y del volcado (`dumper`) se escribieron sobre el formato documentado, sin salidas reales: WPT no estaba instalado y la Preparación requiere el permiso del usuario y admin. Verificación pendiente después de `uv run setup`:
- [ ] Grabar un fixture real (`record-fixture` como admin, con `--duration 10`) y confirmar que `dpc_isr_by_driver.csv` y `processes_top_net.csv` tienen datos.
- [ ] Si el formato real difiere, ajustar `parse_dpcisr` / `parse_network` y reemplazar las muestras de `tests/test_etw.py` por las grabadas.
