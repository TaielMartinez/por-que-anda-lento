# 11: Temperaturas

**What to build:** La Captura incluye el dominio `thermals` desde LibreHardwareMonitor (temperaturas de CPU, placa, discos y GPU; ventiladores; clocks) y su serie temporal en la Ventana de muestreo, para detectar thermal throttling.

**Blocked by:** 05, 08

**Status:** ready-for-agent

- [x] Foto de sensores y serie temporal durante la Ventana de muestreo.
- [x] Sin LibreHardwareMonitor, `thermals` queda `failed` con motivo y el resto de la Captura se genera.
- [x] Resumen: temperatura máxima por componente y caída de clocks.
- [x] Tests con fixtures de lecturas de sensores.
- [x] Documento del dominio `thermals`.
