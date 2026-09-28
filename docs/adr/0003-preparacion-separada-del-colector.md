# Preparación separada del Colector, con descargas automáticas fijadas

Las herramientas de terceros (LibreHardwareMonitor, Sysinternals, pooltag.txt y Windows Performance Toolkit del ADK) se descargan e instalan automáticamente, pero solo en un paso de Preparación separado; el Colector es siempre de solo lectura y, si falta una herramienta, lo registra en el manifest en vez de instalarla. Cada descarga tiene versión fijada y se verifica por SHA256 contra la fuente oficial. Se incluye el ADK pese a su peso porque es la única forma de atribuir la latencia DPC/ISR (causa típica del mouse que "salta") a un driver concreto.

## Consequences

- Actualizar una herramienta implica cambiar a mano su versión y su hash.
- La Preparación es la única parte del proyecto que modifica el sistema; todo lo demás debe poder ejecutarse sin efectos secundarios.
