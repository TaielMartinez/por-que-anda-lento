# 07: Hardware y conexiones

**What to build:** La Captura incluye los dominios `storage` (discos, espacio, SMART), `devices` (PnP, USB, dispositivos con error), `network` (adaptadores, conexiones por proceso), `windows` (ventana en primer plano y ventanas visibles, con títulos) y `software` (instalado).

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Cada dominio en archivos de una sola pregunta, con entradas en el manifest.
- [ ] Si SMART no está disponible para un disco, el dominio no se rompe (`partial` con motivo).
- [ ] Títulos de ventana sin enmascarar.
- [ ] Resumen: espacio libre por volumen, dispositivos con error, conexiones activas.
- [ ] Tests con fixtures de cada dominio.
- [ ] Un documento por dominio.
