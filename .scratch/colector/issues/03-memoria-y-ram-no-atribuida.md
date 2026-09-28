# 03: Memoria y RAM no atribuida

**What to build:** La Captura incluye el dominio `memory` (commit, caché, standby, modificada, compresión, pool paginado y no paginado desglosado por tag, memoria de drivers) y el Resumen responde "¿a dónde se va la RAM?": RAM usada, suma de lo atribuible a procesos, diferencia no atribuida y su descomposición. Es la pregunta original del usuario.

**Blocked by:** 02

**Status:** ready-for-agent

- [x] Archivos separados para totales de memoria, listas de páginas (standby/modificada/libre/zero), compresión y pool por tag (tag, paginado/no paginado, bytes, asignaciones).
- [x] Pool por tag leído vía API nativa (sin herramientas externas); el mapeo tag→driver es el ticket 12.
- [x] Resumen: RAM usada, atribuida a procesos, no atribuida y desglose (pool no paginado, pool paginado, caché, compresión, resto).
- [x] Tests con fixtures, incluido un caso con pool no paginado inflado que se refleja en el Resumen.
- [x] Documento del dominio `memory` explicando cada término y cómo se calcula la RAM no atribuida.
