"""Dominio software: programas instalados (y los instalados hace poco)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from lento.capture import DomainWriter
from lento.cim import parse_iso
from lento.ports import PortError, Ports

NAME = "software"
BASE = "snapshot/software"
DOC = "software"

UNINSTALL_KEYS = [
    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
    "HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
    "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
]
RECENT_DAYS = 30


def collect(ports: Ports, out: DomainWriter) -> None:
    programs: dict[tuple[str, str | None], dict[str, Any]] = {}
    unreadable = []
    for key in UNINSTALL_KEYS:
        try:
            entries = ports.registry_subkey_values(key)
        except PortError as e:
            unreadable.append(f"{key}: {e}")
            continue
        for values in entries.values():
            program = _program(values)
            if program:
                programs.setdefault((program["name"], program["version"]), program)

    # Primero los de fecha conocida, del más reciente al más viejo; después los sin fecha, por nombre.
    dated = sorted((p for p in programs.values() if p["installed_on"]), key=lambda p: p["installed_on"], reverse=True)
    undated = sorted((p for p in programs.values() if not p["installed_on"]), key=lambda p: p["name"])
    installed = dated + undated
    out.json(
        "installed",
        installed,
        "¿Qué programas hay instalados y cuándo se instalaron?",
        "; ".join(unreadable) or None,
    )

    since = (parse_iso(ports.now()).date() - timedelta(days=RECENT_DAYS)).isoformat()
    out.summary().update(
        count=len(installed),
        installed_last_30_days=[
            {"name": p["name"], "version": p["version"], "installed_on": p["installed_on"]}
            for p in dated
            if p["installed_on"] >= since
        ],
    )


def _program(values: dict[str, Any]) -> dict[str, Any] | None:
    name = values.get("DisplayName")
    if not name or values.get("SystemComponent") == 1 or values.get("ParentKeyName"):
        return None
    size_kb = values.get("EstimatedSize")
    return {
        "name": name,
        "version": values.get("DisplayVersion"),
        "publisher": values.get("Publisher"),
        "installed_on": _date(values.get("InstallDate")),
        "size_bytes": size_kb * 1024 if isinstance(size_kb, int) else None,
        "install_location": values.get("InstallLocation") or None,
    }


def _date(value: Any) -> str | None:
    text = str(value or "")
    if len(text) != 8 or not text.isdigit():
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:])).isoformat()
    except ValueError:
        return None
