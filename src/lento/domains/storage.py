"""Dominio storage: volúmenes, discos físicos y contadores de confiabilidad (SMART)."""

from __future__ import annotations

from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "storage"
BASE = "snapshot/storage"
DOC = "storage"

STORAGE_NS = "root\\Microsoft\\Windows\\Storage"
PHYSICAL_DISKS_QUERY = (
    "SELECT DeviceId, FriendlyName, MediaType, BusType, Size, HealthStatus, OperationalStatus, "
    "SpindleSpeed, FirmwareVersion FROM MSFT_PhysicalDisk"
)
RELIABILITY_QUERY = (
    "SELECT DeviceId, Temperature, TemperatureMax, Wear, ReadErrorsTotal, ReadErrorsUncorrected, "
    "WriteErrorsTotal, WriteErrorsUncorrected, PowerOnHours, StartStopCycleCount FROM MSFT_StorageReliabilityCounter"
)

MEDIA_TYPES = {0: "unspecified", 3: "HDD", 4: "SSD", 5: "SCM"}
BUS_TYPES = {7: "USB", 8: "RAID", 10: "SAS", 11: "SATA", 17: "NVMe"}
HEALTH = {0: "healthy", 1: "warning", 2: "unhealthy", 5: "unknown"}


def _label(labels: dict[int, str], value: Any) -> Any:
    return labels.get(value, value) if isinstance(value, int) else value


def collect(ports: Ports, out: DomainWriter) -> None:
    volumes = [_volume(v) for v in ports.disks()]
    out.json("volumes", volumes, "¿Cuánto espacio libre queda en cada volumen?")

    disks = [
        {
            "device_id": d.get("DeviceId"),
            "name": d.get("FriendlyName"),
            "media_type": _label(MEDIA_TYPES, d.get("MediaType")),
            "bus_type": _label(BUS_TYPES, d.get("BusType")),
            "size_bytes": _int(d.get("Size")),
            "health_status": _label(HEALTH, d.get("HealthStatus")),
            "operational_status": d.get("OperationalStatus"),
            "firmware": d.get("FirmwareVersion"),
        }
        for d in ports.wmi(PHYSICAL_DISKS_QUERY, STORAGE_NS)
    ]
    out.json("physical_disks", disks, "¿Qué discos físicos hay, de qué tipo y en qué estado de salud?")

    reason = None
    try:
        smart = [
            {
                "device_id": r.get("DeviceId"),
                "temperature_c": r.get("Temperature"),
                "temperature_max_c": r.get("TemperatureMax"),
                "wear_percent": r.get("Wear"),
                "read_errors_total": _int(r.get("ReadErrorsTotal")),
                "read_errors_uncorrected": _int(r.get("ReadErrorsUncorrected")),
                "write_errors_total": _int(r.get("WriteErrorsTotal")),
                "write_errors_uncorrected": _int(r.get("WriteErrorsUncorrected")),
                "power_on_hours": _int(r.get("PowerOnHours")),
                "start_stop_cycles": _int(r.get("StartStopCycleCount")),
            }
            for r in ports.wmi(RELIABILITY_QUERY, STORAGE_NS)
        ]
    except PortError as e:
        smart, reason = [], str(e)
    out.json(
        "smart",
        smart,
        "¿Qué dicen los contadores de confiabilidad (SMART) de cada disco: temperatura, desgaste, errores?",
        reason,
    )

    with_free = [v for v in volumes if v["free_percent"] is not None]
    lowest = min(with_free, key=lambda v: v["free_percent"], default=None)
    out.summary().update(
        lowest_free_percent=(
            {"mountpoint": lowest["mountpoint"], "free_percent": lowest["free_percent"]} if lowest else None
        ),
        disks_not_healthy=[d["name"] for d in disks if d["health_status"] not in ("healthy", None)],
        max_wear_percent=max((s["wear_percent"] for s in smart if s["wear_percent"] is not None), default=None),
        uncorrected_errors=sum(
            (s["read_errors_uncorrected"] or 0) + (s["write_errors_uncorrected"] or 0) for s in smart
        ),
    )


def _volume(v: dict[str, Any]) -> dict[str, Any]:
    total, free = v.get("total_bytes"), v.get("free_bytes")
    return {
        "mountpoint": v["mountpoint"],
        "fstype": v.get("fstype"),
        "total_bytes": total,
        "used_bytes": v.get("used_bytes"),
        "free_bytes": free,
        "free_percent": round(free / total * 100, 1) if total and free is not None else None,
        "error": v.get("error"),
    }


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
