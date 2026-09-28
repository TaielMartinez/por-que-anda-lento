# Spec: Colector y flujo de Diagnóstico

**Status:** ready-for-agent

## Problem Statement

El usuario tiene una PC Windows potente (i7 8700K, 24 GB de RAM, SSD, RTX 3090) que a veces se traba entera: el mouse se "teletransporta", las animaciones van a tirones. El Administrador de tareas muestra la RAM al 80 %, pero la suma de lo que consumen las aplicaciones visibles es mucho menor y no sabe a dónde se va el resto. Las herramientas de Windows muestran vistas parciales, no dejan registro y no ayudan a razonar sobre la causa; el problema además es intermitente, así que lo que se ve en un instante suele no alcanzar.

## Solution

Un **Colector** en Python que, con una sola ejecución, observa todo lo que se puede observar de la PC y lo guarda como una **Captura**: una **Foto** del estado, una **Ventana de muestreo** con series temporales y un **Historial** de eventos recientes, más un **Resumen** con métricas derivadas neutrales. La Captura se parte en muchos archivos chicos, cada uno respondiendo una sola pregunta, con un índice (manifest) que describe cada archivo; así el agente abre solo lo relevante para el Síntoma sin saturar su contexto.

Sobre el Colector, una skill de agente (`/diagnosticar`) conduce una **Consulta**: pregunta los **Síntomas**, ejecuta el Colector, lee el Resumen y los archivos que necesite, compara contra una **Referencia** si existe, y escribe un **Diagnóstico** con hipótesis, evidencia y recomendaciones. Nada en el flujo modifica el sistema, salvo la **Preparación**, un paso explícito y separado que instala las herramientas externas.

La documentación de la Captura (qué se recopila, dónde, con qué estructura y cómo interpretarlo) vive en el repo, con un índice y un documento por dominio, agnóstica del agente.

## User Stories

1. Como usuario con la PC lenta, quiero contarle al agente lo que noto con mis palabras, para no tener que saber de antemano qué medir.
2. Como usuario, quiero que el agente complete mi relato con preguntas fijas (si está lenta ahora, desde cuándo, con qué frecuencia, si aparece tras horas encendida o tras suspender, qué estaba haciendo, qué se traba, si se arregla solo o reiniciando), para que el Diagnóstico no dependa de lo que se me olvidó mencionar.
3. Como usuario, quiero que mis Síntomas queden guardados en la Consulta, para poder releer después qué reporté.
4. Como usuario, quiero ejecutar el Colector con un único comando, para no tener que armar nada a mano.
5. Como usuario, quiero que el Colector pida elevación con UAC por su cuenta, para que un clic alcance aunque el agente corra sin admin.
6. Como agente, quiero que el Colector me devuelva la ruta de la Captura al terminar, para saber qué leer sin buscarla.
7. Como agente, quiero un manifest que liste cada archivo de la Captura con la pregunta que responde, su tamaño y si está completo, parcial o falló (y por qué), para decidir qué abrir.
8. Como agente, quiero un Resumen con métricas derivadas y sin veredictos, para tener una primera lectura barata antes de abrir archivos detallados.
9. Como usuario, quiero saber cuánta RAM usada no se atribuye a ningún proceso y en qué se descompone (pool no paginado, pool paginado, caché, standby, compresión, memoria de drivers), para entender a dónde se va la RAM.
10. Como agente, quiero el pool del kernel desglosado por tag y traducido al driver dueño, para señalar un driver con fuga de memoria.
11. Como agente, quiero la lista completa de procesos con su árbol, línea de comando, CPU, private bytes, working set, handles, threads e I/O, para entender qué está corriendo y para qué se usa la PC.
12. Como agente, quiero una Ventana de muestreo de duración configurable (por defecto 60 s, cada 1 s), para ver picos y tendencias que una Foto no muestra.
13. Como agente, quiero poder pedir una Ventana de muestreo más larga cuando el Síntoma es esporádico, para aumentar la chance de capturarlo.
14. Como agente, quiero series de CPU por núcleo, % DPC time, % interrupt time, cola de disco, hard page faults y memoria disponible, cada una en su archivo, para abrir solo la métrica que me interesa.
15. Como agente, quiero un top 20 de procesos por cada recurso (CPU, RAM, disco, red, GPU) en archivos separados, para leer solo el recurso relacionado con el Síntoma.
16. Como agente, quiero que el top de RAM incluya cuánto creció cada proceso durante la Ventana de muestreo, para detectar fugas lentas.
17. Como agente, quiero además un archivo con todos los procesos en cada muestra, para cuando el top no alcance.
18. Como usuario con el mouse que salta, quiero saber qué driver genera latencia DPC/ISR, para saber qué actualizar o deshabilitar.
19. Como agente, quiero el tráfico de red por proceso durante la Ventana de muestreo, para detectar procesos que saturan la red.
20. Como agente, quiero el estado de la GPU (uso, VRAM, temperatura, clocks, procesos), para descartar o confirmar problemas gráficos.
21. Como agente, quiero las temperaturas de CPU, placa, discos y GPU, ventiladores y clocks, para detectar thermal throttling.
22. Como agente, quiero el estado de los discos (espacio, SMART, cola), para detectar un disco lleno o degradado.
23. Como agente, quiero los dispositivos conectados (PnP, USB) y los que tienen error, para detectar hardware problemático.
24. Como agente, quiero los drivers con versión, fecha y firma, para señalar drivers viejos o sin firmar.
25. Como agente, quiero los servicios, programas de inicio y tareas programadas, para detectar carga innecesaria.
26. Como agente, quiero saber si Defender está escaneando o Windows Update está trabajando, para distinguir lentitud transitoria de un problema real.
27. Como agente, quiero la ventana en primer plano y las ventanas visibles, para saber qué estaba haciendo el usuario.
28. Como agente, quiero el software instalado, para contextualizar lo que corre.
29. Como agente, quiero los adaptadores de red y las conexiones por proceso, para entender qué tiene conectado la PC.
30. Como agente, quiero la configuración del sistema (hardware, OS, uptime, plan de energía, Game Mode, HAGS), para contextualizar todo lo demás.
31. Como agente, quiero los eventos de los últimos 7 días (disco, WHEA, Resource Exhaustion, Diagnostics-Performance, TDR de GPU) con un tope por fuente, para ver si el Síntoma es un patrón o un caso aislado.
32. Como usuario, quiero que una Captura tomada con la PC andando bien quede como Referencia, para comparar la próxima vez que se trabe.
33. Como agente, quiero saber qué Captura es la Referencia vigente, para comparar sin preguntarle al usuario.
34. Como agente, quiero registrar en la Consulta qué Captura analicé y contra qué Referencia, para que el Diagnóstico sea reproducible.
35. Como usuario, quiero un Diagnóstico con hipótesis ordenadas por probabilidad y la evidencia de cada una (archivo y valor), para poder verificarlo.
36. Como usuario, quiero que el Diagnóstico diga qué se descartó y por qué, para no perseguir pistas falsas.
37. Como usuario, quiero recomendaciones concretas que aplicaré yo, para mantener el control de mi PC.
38. Como usuario, quiero que, si los datos no alcanzan, el Diagnóstico diga qué Captura tomar y cuándo, para avanzar en la próxima Consulta.
39. Como usuario, quiero que ni el Colector ni el agente modifiquen el sistema, para no empeorar las cosas.
40. Como usuario, quiero un comando de Preparación que descargue e instale las herramientas externas con versión fijada y hash verificado, para confiar en lo que se instala.
41. Como usuario, quiero que la Preparación sea idempotente, para poder correrla de nuevo sin romper nada.
42. Como agente, quiero que, si falta una herramienta, el Colector siga con el resto y lo registre en el manifest, para saber qué datos no tengo y ofrecer correr la Preparación.
43. Como usuario, quiero que las trazas ETW pesadas se procesen y se borren salvo que pida conservarlas, para no llenar el disco.
44. Como usuario, quiero que las Capturas no se borren solas, para decidir yo qué conservar.
45. Como agente de cualquier marca, quiero una documentación de la Captura con un índice y un documento por dominio (campos, unidades, cómo interpretarlos), para leer solo la del dominio que investigo.
46. Como mantenedor, quiero que cada dominio llegue con su documentación y sus tests, para que la documentación nunca quede atrasada respecto de los datos.
47. Como usuario sin GPU NVIDIA, quiero datos de GPU igual (contadores genéricos), para que el Colector sirva en otras PCs Windows 10/11.

## Implementation Decisions

- **Stack:** Python gestionado con uv (`pyproject.toml`). Dos puntos de entrada: `collect` (Colector) y `setup` (Preparación).
- **Idioma:** código, nombres de archivo y claves JSON en inglés; documentación y vocabulario de dominio en español (ver `CONTEXT.md`).
- **Solo lectura:** el Colector nunca modifica el sistema ni instala nada. La Preparación es lo único que lo hace (ADR 0003).
- **Privilegios:** el Colector exige admin y se auto-eleva con UAC; el proceso no elevado espera al elevado y emite la ruta de la Captura (ADR 0002).
- **Sin filtrado:** se capturan líneas de comando, títulos de ventana y demás datos sin enmascarar (ADR 0001).
- **Puertos hacia Windows:** todo acceso al sistema pasa por un conjunto chico de puertos de lectura cruda: ejecutar un comando externo, consultar WMI, leer contadores de rendimiento, enumerar procesos, llamar APIs nativas (información de sistema/pool/memoria), leer el log de eventos y leer sensores. Los módulos de dominio solo dependen de esos puertos.
- **Módulos de dominio:** uno por dominio de la Foto (`system`, `memory`, `processes`, `services`, `startup`, `scheduled_tasks`, `gpu`, `thermals`, `storage`, `network`, `devices`, `drivers`, `windows`, `software`, `security`, `updates`), más el muestreo, el Historial y el cálculo del Resumen. Un dominio que falla no aborta la Captura: queda registrado como fallido en el manifest.
- **Estructura de la Captura** (contrato con el agente):
  - Una carpeta por Captura, identificada por fecha y hora, bajo un directorio de capturas ignorado por git.
  - `manifest.json`: metadatos de la Captura (versión del esquema, inicio/fin, duración de la Ventana de muestreo, si es Referencia, herramientas faltantes) y una entrada por archivo con ruta, pregunta que responde, tamaño y estado (`complete` / `partial` / `failed` + motivo). Explica el criterio de cada top.
  - `summary.json`: el Resumen, solo números derivados, sin veredictos.
  - Foto: un subdirectorio por dominio, partido en archivos que responden una sola pregunta (por ejemplo, procesos en lista, árbol, líneas de comando, I/O y handles por separado).
  - Ventana de muestreo: un CSV por métrica; `processes_all` con todos los procesos por muestra; un top 20 por recurso en archivos separados (CPU, RAM con delta de private bytes, disco, red, GPU); DPC/ISR por driver.
  - Historial: eventos de 7 días, un archivo por fuente, con tope de eventos.
  - Salidas crudas de herramientas externas en un subdirectorio aparte.
- **Consultas:** viven en un directorio propio, separado de las Capturas. Cada una contiene `symptoms.md`, `captures.json` (Captura analizada y Referencia usada) y `diagnosis.md`. Una Captura puede usarse en varias Consultas.
- **Referencia:** una Captura se marca como Referencia cuando el usuario indica que la PC anda bien al momento de capturar; la marca queda en su manifest.
- **Ventana de muestreo:** 60 s por defecto, intervalo de 1 s, ambos configurables por argumento.
- **ETW:** durante la Ventana de muestreo se graba una traza con WPR; se procesa con xperf a DPC/ISR por driver y tráfico de red por proceso; el `.etl` se borra salvo `--keep-etl`.
- **Herramientas externas:** LibreHardwareMonitor, Sysinternals (autorunsc, sigcheck, handle), pooltag.txt y Windows Performance Toolkit del ADK. Versiones fijadas y SHA256 en un manifiesto de herramientas; se descargan a una carpeta ignorada por git.
- **GPU:** nvidia-smi si existe; si no, contadores genéricos `GPU Engine`.
- **Retención:** las Capturas no se borran automáticamente.
- **Skill `/diagnosticar`:** skill de Claude Code en el repo que conduce la Consulta: relato libre, checklist de Síntomas, Preparación si falta, Colector (con duración elegida según el Síntoma), lectura de manifest y Resumen, apertura selectiva de archivos y documentación de dominio, comparación con Referencia, escritura del Diagnóstico. El Diagnóstico contiene hipótesis ordenadas con evidencia (archivo + valor), descartes, recomendaciones que aplica el usuario y, si hace falta, qué Captura tomar después.
- **Documentación de la Captura:** un índice (estructura de carpetas, manifest, Resumen, cómo navegar) y un documento por dominio con campos, unidades e interpretación.

## Testing Decisions

- **Una sola costura:** los puertos hacia Windows. Los tests ejecutan el Colector completo con esos puertos reemplazados por fixtures grabadas de salidas reales de la PC del usuario, y verifican solo el resultado externo: qué archivos existen en la Captura, el contenido de `manifest.json` (incluidos estados parciales y fallidos), el contenido de cada archivo, el Resumen y los tops.
- **Buen test:** describe comportamiento observable de la Captura ("con esta salida de nvidia-smi, el dominio gpu reporta X y el manifest lo marca completo"; "si falta LibreHardwareMonitor, thermals queda `failed` con motivo y el resto de la Captura se genera"). No verifica funciones internas ni cómo se reparte el código.
- **Fixtures:** se graban desde esta PC a través de los mismos puertos, así el parseo de herramientas (nvidia-smi, xperf, autorunsc, sigcheck, LibreHardwareMonitor) queda cubierto.
- **Prueba de humo real:** marcada aparte y fuera de la corrida por defecto; ejecuta el Colector de verdad con admin y ~10 s de muestreo y valida la Captura contra el esquema documentado.
- **Sin test automático:** la auto-elevación por UAC y la Preparación (checklist manual en sus tickets); la skill `/diagnosticar` (es prompt).
- **Prior art:** no hay código previo en el repo; el primer ticket establece la base de tests.

## Out of Scope

- Aplicar correcciones al sistema (matar procesos, deshabilitar servicios, actualizar drivers).
- Grabador en segundo plano que corra horas o días esperando el Síntoma (el formato no debe impedirlo a futuro).
- Enmascarar o redactar datos sensibles.
- Sistemas operativos distintos de Windows 10/11.
- Limpieza automática de Capturas.
- Interfaz gráfica.

## Further Notes

- Vocabulario: ver `CONTEXT.md`. Decisiones: ADRs 0001–0003.
- Hipótesis iniciales para el caso del usuario, a confirmar con datos: fuga en el pool no paginado por un driver (RAM "invisible") y latencia DPC/ISR de un driver (mouse que salta). Los tickets 03, 12 y 13 apuntan a ellas.
