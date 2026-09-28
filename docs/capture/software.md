# Dominio `software`

Parte de la **Foto**. Carpeta: `snapshot/software/`. Programas instalados, leídos de las claves "Desinstalar" del registro (de la máquina, de 32 bits y del usuario). Se omiten los componentes del sistema y las actualizaciones que dependen de otro programa.

## Archivos

### `installed`: ¿Qué programas hay instalados y cuándo se instalaron?

Primero los que tienen fecha, del más reciente al más viejo, y al final los que no tienen, por nombre. Campos: `name`, `version`, `publisher`, `installed_on` (`AAAA-MM-DD`, o `null` si el instalador no la registra), `size_bytes`, `install_location`.

**Cómo interpretarlo.** Cruzar `installed_on` con la respuesta "¿desde cuándo pasa?" de los Síntomas: un driver, un antivirus o una utilidad de RGB/overlay instalados justo antes de que empiece la lentitud son sospechosos. Algunos programas reescriben la fecha al actualizarse.

## Sección del Resumen (`summary.software`)

| Campo | Qué es |
|---|---|
| `count` | Programas instalados. |
| `installed_last_30_days` | `name`, `version` e `installed_on` de lo instalado o actualizado en los últimos 30 días. |
