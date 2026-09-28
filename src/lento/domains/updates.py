"""Dominio updates: ¿Windows Update está trabajando?, ¿hay un reinicio pendiente? y actualizaciones recientes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "updates"
BASE = "snapshot/updates"
DOC = "updates"

SERVICES_QUERY = (
    "SELECT Name, State FROM Win32_Service WHERE Name = 'wuauserv' OR Name = 'TrustedInstaller' "
    "OR Name = 'UsoSvc' OR Name = 'BITS'"
)
REBOOT_REQUIRED_KEY = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired"
CBS_REBOOT_KEY = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending"
HOTFIX_QUERY = "SELECT HotFixID, Description, InstalledOn FROM Win32_QuickFixEngineering"


def collect(ports: Ports, out: DomainWriter) -> None:
    services = {s["Name"]: s.get("State") for s in ports.wmi(SERVICES_QUERY)}
    activity = {
        "services": services,
        # TrustedInstaller solo corre mientras se instalan o configuran componentes.
        "installing": services.get("TrustedInstaller") == "Running",
        "pending_reboot": _exists(ports, REBOOT_REQUIRED_KEY) or _exists(ports, CBS_REBOOT_KEY),
    }
    out.json("activity", activity, "¿Windows Update está instalando algo ahora y hay un reinicio pendiente?")

    installed = sorted(
        (
            {"id": h.get("HotFixID"), "description": h.get("Description"), "installed_on": _date(h.get("InstalledOn"))}
            for h in ports.wmi(HOTFIX_QUERY)
        ),
        key=lambda h: h["installed_on"] or "",
        reverse=True,
    )
    out.json("installed", installed, "¿Qué actualizaciones de Windows se instalaron y cuándo?")

    out.summary().update(
        installing=activity["installing"],
        pending_reboot=activity["pending_reboot"],
        last_installed_on=installed[0]["installed_on"] if installed else None,
    )


def _exists(ports: Ports, key: str) -> bool:
    try:
        ports.registry_values(key)
        return True
    except PortError:
        return False


def _date(value: Any) -> str | None:
    for fmt in ("%m/%d/%Y", "%Y%m%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            continue
    return None
