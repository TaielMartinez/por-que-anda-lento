# 10: GPU

**What to build:** La Captura incluye el dominio `gpu` (uso, VRAM, temperatura, clocks, procesos) leído con nvidia-smi, o con los contadores genéricos `GPU Engine` si no hay NVIDIA; y la Ventana de muestreo agrega la serie de GPU y el top 20 de procesos por GPU en su propio archivo.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Foto de GPU desde nvidia-smi; fallback a contadores genéricos, con el origen indicado en el manifest.
- [ ] Serie temporal de uso de GPU y VRAM en la Ventana de muestreo.
- [ ] Top 20 por GPU (uso de motor + VRAM dedicada) en archivo separado.
- [ ] Resumen: picos de uso y de VRAM.
- [ ] Tests con fixtures de nvidia-smi y de contadores genéricos.
- [ ] Documento del dominio `gpu`.
