# Por qué anda lento

Herramienta para diagnosticar por qué una PC Windows anda lenta: un colector junta todo lo que se puede observar del sistema y un agente lo analiza a la luz de los síntomas que describe el usuario.

## Language

**Síntoma**:
Lo que el usuario percibe y reporta con sus palabras (el mouse salta, las animaciones van a tirones, la RAM figura alta). Es el punto de partida del análisis, no un dato medido.
_Avoid_: Problema, error, falla

**Colector**:
El programa que observa el sistema y produce una Captura. Solo lee: nunca modifica el sistema.
_Avoid_: Scanner, script, recolector

**Captura**:
El conjunto de datos que produce una ejecución del Colector: una Foto, una Ventana de muestreo y un Historial del mismo momento, más su Resumen. Contiene solo datos observados, nunca Síntomas ni Diagnósticos.
_Avoid_: Snapshot, dump, reporte

**Foto**:
La parte de una Captura que refleja el estado del sistema en un único instante.
_Avoid_: Snapshot, estado

**Ventana de muestreo**:
La parte de una Captura que mide el sistema repetidamente durante un lapso configurable, para ver picos y tendencias.
_Avoid_: Monitoreo, grabación

**Historial**:
La parte de una Captura que refleja lo que pasó antes de ejecutarla (eventos del sistema de los últimos días).
_Avoid_: Logs, pasado

**Referencia**:
Una Captura tomada mientras la PC anda bien, que se usa como línea base para comparar con Capturas tomadas durante un Síntoma.
_Avoid_: Baseline, captura normal

**Resumen**:
Métricas derivadas y neutrales calculadas a partir de una Captura (por ejemplo, cuánta RAM usada no se atribuye a ningún proceso). Contiene números, no veredictos.
_Avoid_: Diagnóstico, hallazgos, conclusiones

**Consulta**:
Una conversación entre el usuario y el agente sobre la lentitud: reúne los Síntomas, las Capturas analizadas (y la Referencia usada, si hubo) y termina en un Diagnóstico. Las Capturas no pertenecen a una Consulta; una misma Captura puede usarse en varias.
_Avoid_: Sesión, caso, ticket

**Diagnóstico**:
La explicación de la lentitud con la que termina una Consulta: hipótesis con evidencia, descartes, recomendaciones y, si hace falta, qué Captura tomar después. Nunca incluye cambios aplicados al sistema.
_Avoid_: Análisis automático, fix, solución

**Preparación**:
El paso, separado del Colector, que deja lista la PC para capturar (descarga e instala herramientas externas). Es lo único del proyecto que modifica el sistema.
_Avoid_: Setup, instalación
