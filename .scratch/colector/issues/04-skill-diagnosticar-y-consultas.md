# 04: Skill /diagnosticar y Consultas

**What to build:** El usuario invoca `/diagnosticar` en Claude Code y el agente conduce una Consulta completa: pide el relato libre, completa con la checklist de Síntomas, ejecuta el Colector, lee manifest y Resumen, abre solo los archivos y documentos de dominio relevantes, compara contra la Referencia si existe y escribe el Diagnóstico. Si la PC no está lenta ahora, la Captura queda marcada como Referencia.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Skill de proyecto invocable como `/diagnosticar`.
- [ ] Checklist de Síntomas: ¿lenta ahora?, desde cuándo, frecuencia, tras horas encendida o tras suspender, qué hacía, qué se traba, si se arregla solo o reiniciando.
- [ ] Cada Consulta tiene su carpeta, separada de las Capturas, con `symptoms.md`, `captures.json` (Captura analizada y Referencia usada) y `diagnosis.md`.
- [ ] El Colector acepta marcar la Captura como Referencia; la marca queda en el manifest y el agente puede encontrar la Referencia vigente.
- [ ] El agente elige la duración de la Ventana de muestreo según el Síntoma (cuando exista el ticket 05).
- [ ] Si faltan herramientas (según el manifest), el agente ofrece correr la Preparación.
- [ ] `diagnosis.md`: hipótesis ordenadas con evidencia (archivo + valor), descartes, recomendaciones que aplica el usuario y próxima Captura sugerida si los datos no alcanzan.
- [ ] El agente no aplica cambios al sistema.
- [ ] Verificación manual: una Consulta real en esta PC.
