# Dominio `network`

Parte de la **Foto**. Carpeta: `snapshot/network/`. Adaptadores y conexiones abiertas. El tráfico por proceso a lo largo del tiempo está en la Ventana de muestreo (`processes_top_net`, cuando está la traza ETW).

## Archivos

### `adapters`: ¿Qué adaptadores de red físicos hay, cuáles están conectados y a qué velocidad?

`name`, `connection_name` (el nombre que se ve en Windows, por ejemplo "Ethernet" o "Wi-Fi"), `enabled` (conectado), `speed_bps`, `mac`, `type`, `manufacturer`. Un Ethernet a 100 Mbps en lugar de 1 Gbps indica un problema de cable o de negociación.

### `ip_config`: ¿Qué direcciones IP, gateway y DNS usa cada adaptador?

`adapter`, `addresses`, `gateways`, `dns_servers`, `dhcp`.

### `connections`: ¿Qué conexiones de red tiene abiertas cada proceso?

Una fila por socket: `pid`, `process_name`, `protocol` (`tcp`/`udp`), `family`, `local_address`, `remote_address`, `status` (`ESTABLISHED`, `LISTEN`, `TIME_WAIT`...). Miles de conexiones en un mismo proceso pueden indicar una fuga de sockets o un cliente P2P.

## Sección del Resumen (`summary.network`)

| Campo | Qué es |
|---|---|
| `connected_adapters` | Adaptadores conectados con su velocidad. |
| `connections_by_status` | Cantidad de conexiones por estado. |
| `top_processes_by_connections` | Los 5 procesos con más conexiones. |
