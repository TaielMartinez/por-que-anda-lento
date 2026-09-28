# 11: Temperaturas

**What to build:** La Captura incluye el dominio `thermals` desde LibreHardwareMonitor (temperaturas de CPU, placa, discos y GPU; ventiladores; clocks) y su serie temporal en la Ventana de muestreo, para detectar thermal throttling.

**Blocked by:** 05, 08

**Status:** ready-for-agent

- [ ] Foto de sensores y serie temporal durante la Ventana de muestreo.
- [ ] Sin LibreHardwareMonitor, `thermals` queda `failed` con motivo y el resto de la Captura se genera.
- [ ] Resumen: temperatura máxima por componente y caída de clocks.
- [ ] Tests con fixtures de lecturas de sensores.
- [ ] Documento del dominio `thermals`.
