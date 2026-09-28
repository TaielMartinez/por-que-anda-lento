"""Dominio startup: qué arranca con Windows y al iniciar sesión."""

from __future__ import annotations

import csv
import io
from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "startup"
BASE = "snapshot/startup"
DOC = "startup"

# -a lb: inicio de sesión y boot execute; -c: CSV; -s: verificar firmas; *: todos los usuarios.
AUTORUNS_ARGS = ["-accepteula", "-nobanner", "-a", "lb", "-c", "-s", "*"]

RUN_KEYS = [
    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
    "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run",
    "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
]


def collect(ports: Ports, out: DomainWriter) -> None:
    tool = _tool(ports, "autorunsc")
    reason = None
    if tool:
        result = ports.run([tool, *AUTORUNS_ARGS], 300)
        entries = _parse_autoruns(result["stdout"])
        if result["returncode"] != 0 and not entries:
            reason = f"autorunsc terminó con código {result['returncode']}: {result['stderr'][:200]}"
    else:
        entries = _run_keys(ports)
        reason = "autorunsc no instalado (correr la Preparación): solo se leyeron las claves Run del registro"
    out.json("entries", entries, "¿Qué programas se ejecutan al arrancar Windows o al iniciar sesión?", reason)

    enabled = [e for e in entries if e["enabled"] is True]
    out.summary().update(
        count=len(entries),
        enabled_count=len(enabled),
        not_verified=[e["entry"] for e in enabled if (e.get("signer") or "").startswith("(Not Verified)")],
    )


def _parse_autoruns(text: str) -> list[dict[str, Any]]:
    lines = [line for line in text.splitlines() if line.strip()]
    entries = []
    for row in csv.DictReader(io.StringIO("\n".join(lines))):
        if not row.get("Entry"):
            continue  # filas de ubicación sin entradas
        entries.append({
            "entry": row["Entry"],
            "location": row.get("Entry Location"),
            "enabled": (row.get("Enabled") or "").lower() == "enabled",
            "category": row.get("Category"),
            "profile": row.get("Profile"),
            "description": row.get("Description"),
            "signer": row.get("Signer"),
            "company": row.get("Company"),
            "image_path": row.get("Image Path"),
            "version": row.get("Version"),
            "launch_string": row.get("Launch String"),
            "registered_at": row.get("Time"),
            "source": "autoruns",
        })
    return entries


def _run_keys(ports: Ports) -> list[dict[str, Any]]:
    entries = []
    for key in RUN_KEYS:
        try:
            values = ports.registry_values(key)
        except PortError:
            continue
        for name, command in values.items():
            entries.append({
                "entry": name,
                "location": key,
                "enabled": None,  # la habilitación vive en StartupApproved; Autoruns la resuelve
                "launch_string": command,
                "source": "registry",
            })
    return entries


def _tool(ports: Ports, name: str) -> str | None:
    try:
        return ports.tool_path(name)
    except PortError:
        return None
