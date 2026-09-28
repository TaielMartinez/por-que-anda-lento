# 06: Historial

**What to build:** La Captura incluye el Historial: eventos de los últimos 7 días de las fuentes relevantes para la lentitud (errores de disco, WHEA, Resource Exhaustion Detector, Diagnostics-Performance, TDR de GPU, reinicios inesperados), un archivo por fuente con tope de eventos, para que el agente vea si el Síntoma es un patrón o un caso aislado.

**Blocked by:** 01

**Status:** ready-for-agent

- [x] Un archivo por fuente con tope configurable; el manifest indica si se truncó.
- [x] Fuentes inaccesibles quedan `partial`/`failed` con motivo.
- [x] Resumen: cantidad de eventos por fuente y por día.
- [x] Tests con fixtures de eventos grabados.
- [x] Documento del Historial con qué significa cada fuente.
