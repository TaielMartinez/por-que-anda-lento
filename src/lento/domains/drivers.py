"""Dominio drivers: drivers cargados, versión y fecha de los drivers de dispositivos, y firmas."""

from __future__ import annotations

import csv
import io
from typing import Any

from lento.capture import DomainWriter
from lento.cim import parse_cim_datetime
from lento.ports import PortError, Ports

NAME = "drivers"
BASE = "snapshot/drivers"
DOC = "drivers"

LOADED_QUERY = "SELECT Name, DisplayName, State, StartMode, PathName FROM Win32_SystemDriver WHERE State = 'Running'"
SIGNED_DRIVERS_QUERY = (
    "SELECT DeviceName, DriverVersion, DriverDate, DriverProviderName, IsSigned, InfName FROM Win32_PnPSignedDriver"
)
# -u: solo archivos sin firma válida; -e: solo imágenes ejecutables; -c: CSV.
SIGCHECK_ARGS = ["-accepteula", "-nobanner", "-c", "-u", "-e", "C:\\Windows\\System32\\drivers"]

OLDEST_IN_SUMMARY = 5


def collect(ports: Ports, out: DomainWriter) -> None:
    loaded = sorted(
        (
            {
                "name": d.get("Name"),
                "display_name": d.get("DisplayName"),
                "start_mode": d.get("StartMode"),
                "path": d.get("PathName"),
            }
            for d in ports.wmi(LOADED_QUERY)
        ),
        key=lambda d: (d["name"] or "").lower(),
    )
    out.json("loaded", loaded, "¿Qué drivers de kernel están cargados?")

    device_drivers = sorted(
        (
            {
                "device": d.get("DeviceName"),
                "provider": d.get("DriverProviderName"),
                "version": d.get("DriverVersion"),
                "date": _date(d.get("DriverDate")),
                "signed": d.get("IsSigned"),
                "inf": d.get("InfName"),
            }
            for d in ports.wmi(SIGNED_DRIVERS_QUERY)
            if d.get("DeviceName")
        ),
        key=lambda d: d["date"] or "9999",
    )
    out.json("device_drivers", device_drivers, "¿Qué versión y fecha tiene el driver de cada dispositivo?")

    tool = _tool(ports, "sigcheck")
    if tool:
        unsigned: list[dict[str, Any]] = _parse_sigcheck(ports.run([tool, *SIGCHECK_ARGS], 300)["stdout"])
        reason = None
        unsigned_names = [u["path"] for u in unsigned]
    else:
        unsigned = [
            {"device": d["device"], "provider": d["provider"], "version": d["version"], "inf": d["inf"]}
            for d in device_drivers
            if d["signed"] is False
        ]
        reason = "sigcheck no instalado (correr la Preparación): solo drivers de dispositivos según Windows"
        unsigned_names = [u["device"] for u in unsigned]
    out.json("unsigned", unsigned, "¿Qué drivers no tienen una firma digital válida?", reason)

    third_party = [d for d in device_drivers if d["date"] and "microsoft" not in (d["provider"] or "").lower()]
    out.summary().update(
        loaded_count=len(loaded),
        unsigned=unsigned_names,
        oldest_third_party=[
            {"device": d["device"], "provider": d["provider"], "date": d["date"], "version": d["version"]}
            for d in third_party[:OLDEST_IN_SUMMARY]
        ],
    )


def _parse_sigcheck(text: str) -> list[dict[str, Any]]:
    lines = [line for line in text.splitlines() if line.strip()]
    return [
        {
            "path": row.get("Path"),
            "verified": row.get("Verified"),
            "company": row.get("Company"),
            "description": row.get("Description"),
            "file_version": row.get("File Version"),
            "date": row.get("Date"),
        }
        for row in csv.DictReader(io.StringIO("\n".join(lines)))
        if row.get("Path")
    ]


def _date(value: Any) -> str | None:
    dt = parse_cim_datetime(value)
    return dt.date().isoformat() if dt else None


def _tool(ports: Ports, name: str) -> str | None:
    try:
        return ports.tool_path(name)
    except PortError:
        return None
