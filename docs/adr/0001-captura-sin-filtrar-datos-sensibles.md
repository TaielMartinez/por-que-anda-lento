# Captura sin filtrar datos sensibles

El Colector guarda líneas de comando completas, títulos de ventana, conexiones de red y software instalado sin enmascarar nada, aunque la Captura la lea un agente que corre en un LLM en la nube. El usuario lo decidió así porque cualquier filtro (por patrón o por omisión) puede esconder justo el dato que explica la lentitud, y la PC es suya. No "arreglar" esto agregando redacción sin volver a discutirlo.

## Considered Options

- Enmascarar patrones que parecen secretos (tokens, `password=`, claves largas): descartado por el usuario.
- No capturar títulos de ventana ni líneas de comando: descartado; pierde el "para qué se está usando la PC".
