"""Dominio network: adaptadores, configuración IP y conexiones por proceso."""

from __future__ import annotations

from collections import Counter

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "network"
BASE = "snapshot/network"
DOC = "network"

ADAPTERS_QUERY = (
    "SELECT Name, NetConnectionID, NetEnabled, Speed, MACAddress, AdapterType, Manufacturer "
    "FROM Win32_NetworkAdapter WHERE PhysicalAdapter = TRUE"
)
IP_QUERY = (
    "SELECT Description, IPAddress, DefaultIPGateway, DNSServerSearchOrder, DHCPEnabled "
    "FROM Win32_NetworkAdapterConfiguration WHERE IPEnabled = TRUE"
)


def collect(ports: Ports, out: DomainWriter) -> None:
    adapters = [
        {
            "name": a.get("Name"),
            "connection_name": a.get("NetConnectionID"),
            "enabled": a.get("NetEnabled"),
            "speed_bps": int(a["Speed"]) if a.get("Speed") else None,
            "mac": a.get("MACAddress"),
            "type": a.get("AdapterType"),
            "manufacturer": a.get("Manufacturer"),
        }
        for a in ports.wmi(ADAPTERS_QUERY)
    ]
    out.json("adapters", adapters, "¿Qué adaptadores de red físicos hay, cuáles están conectados y a qué velocidad?")

    ip = [
        {
            "adapter": c.get("Description"),
            "addresses": c.get("IPAddress"),
            "gateways": c.get("DefaultIPGateway"),
            "dns_servers": c.get("DNSServerSearchOrder"),
            "dhcp": c.get("DHCPEnabled"),
        }
        for c in ports.wmi(IP_QUERY)
    ]
    out.json("ip_config", ip, "¿Qué direcciones IP, gateway y DNS usa cada adaptador?")

    conns = ports.connections()
    out.json("connections", conns, "¿Qué conexiones de red tiene abiertas cada proceso?")

    by_process = Counter(c.get("process_name") or f"pid {c.get('pid')}" for c in conns)
    out.summary().update(
        connected_adapters=[
            {"name": a["connection_name"] or a["name"], "speed_bps": a["speed_bps"]}
            for a in adapters
            if a["enabled"]
        ],
        connections_by_status=dict(Counter(c.get("status") for c in conns)),
        top_processes_by_connections=[{"process": p, "connections": n} for p, n in by_process.most_common(5)],
    )
