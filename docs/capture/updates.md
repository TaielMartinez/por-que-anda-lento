# Dominio `updates`

Parte de la **Foto**. Carpeta: `snapshot/updates/`. Windows Update puede consumir CPU y disco durante minutos (TiWorker, TrustedInstaller). Es una causa típica de lentitud transitoria "después de prender la PC".

## Archivos

### `activity`: ¿Windows Update está instalando algo ahora y hay un reinicio pendiente?

- `services`: estado de `wuauserv`, `TrustedInstaller`, `UsoSvc` y `BITS`.
- `installing`: `true` si `TrustedInstaller` está corriendo, lo que solo pasa mientras se instalan o configuran componentes.
- `pending_reboot`: `true` si Windows espera un reinicio para terminar una actualización.

### `installed`: ¿Qué actualizaciones de Windows se instalaron y cuándo?

`id` (KB), `description` e `installed_on`, de la más reciente a la más vieja. Sirve para cruzar con el "¿desde cuándo pasa?" de los Síntomas.

## Sección del Resumen (`summary.updates`)

| Campo | Qué es |
|---|---|
| `installing` | Instalación en curso. |
| `pending_reboot` | Reinicio pendiente. |
| `last_installed_on` | Fecha de la última actualización instalada. |
