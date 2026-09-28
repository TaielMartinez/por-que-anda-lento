"""Dominio services: servicios de Windows, su estado y cómo arrancan."""

from __future__ import annotations

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "services"
BASE = "snapshot/services"
DOC = "services"

QUERY = "SELECT Name, DisplayName, State, StartMode, PathName, ProcessId, StartName FROM Win32_Service"


def collect(ports: Ports, out: DomainWriter) -> None:
    services = sorted(
        (
            {
                "name": s.get("Name"),
                "display_name": s.get("DisplayName"),
                "state": s.get("State"),
                "start_mode": s.get("StartMode"),
                "pid": s.get("ProcessId") or None,
                "account": s.get("StartName"),
                "command": s.get("PathName"),
            }
            for s in ports.wmi(QUERY)
        ),
        key=lambda s: (s["name"] or "").lower(),
    )
    out.json("list", services, "¿Qué servicios existen, en qué estado están y cómo arrancan?")
    running = [s for s in services if s["state"] == "Running"]
    out.json("running", running, "¿Qué servicios están corriendo ahora y en qué proceso?")
    out.summary().update(
        count=len(services),
        running_count=len(running),
        auto_start_count=sum(1 for s in services if s["start_mode"] == "Auto"),
        auto_start_not_running=[s["name"] for s in services if s["start_mode"] == "Auto" and s["state"] != "Running"],
    )
