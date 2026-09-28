# 12: Pool tags con driver dueño

**What to build:** Cada tag del pool del kernel se traduce al driver responsable usando pooltag.txt y los binarios de los drivers instalados, y el Resumen señala qué driver retiene más pool, para convertir la "RAM no atribuida" en un culpable concreto.

**Blocked by:** 03, 08

**Status:** ready-for-agent

- [ ] Archivo con tag → driver(s) candidato(s) y origen del mapeo (pooltag.txt o búsqueda en binarios).
- [ ] Los tags sin mapeo se reportan como desconocidos, no se omiten.
- [ ] Sin pooltag.txt, el dominio queda `partial` con motivo.
- [ ] Resumen: top de drivers por pool no paginado y paginado.
- [ ] Tests con fixtures de pool y un pooltag.txt reducido.
- [ ] Documento del dominio `memory` actualizado.
