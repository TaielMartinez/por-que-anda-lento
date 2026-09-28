"""Dominio devices: dispositivos PnP, USB y dispositivos con error."""

from __future__ import annotations

from typing import Any

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "devices"
BASE = "snapshot/devices"
DOC = "devices"

PNP_QUERY = (
    "SELECT Name, PNPClass, Manufacturer, Status, ConfigManagerErrorCode, PNPDeviceID, Present "
    "FROM Win32_PnPEntity"
)

# Códigos del Administrador de dispositivos más frecuentes.
ERROR_MEANINGS = {
    1: "el dispositivo no está configurado correctamente",
    3: "el driver puede estar dañado o falta memoria",
    10: "el dispositivo no puede iniciar",
    12: "no hay recursos libres suficientes (conflicto)",
    14: "hace falta reiniciar",
    18: "hay que reinstalar los drivers",
    19: "configuración del registro dañada",
    22: "el dispositivo está deshabilitado",
    24: "el dispositivo no está presente o falta un driver",
    28: "los drivers no están instalados",
    31: "el dispositivo no funciona correctamente",
    32: "el servicio del driver está deshabilitado",
    39: "no se pudo cargar el driver (dañado o ausente)",
    43: "Windows detuvo el dispositivo porque informó problemas",
    45: "el dispositivo no está conectado",
    52: "la firma digital del driver no es válida",
}


def collect(ports: Ports, out: DomainWriter) -> None:
    rows = [_device(d) for d in ports.wmi(PNP_QUERY)]
    rows.sort(key=lambda d: (d["class"] or "", d["name"] or ""))
    out.json("all", rows, "¿Qué dispositivos reconoce Windows?")

    problems = [d for d in rows if d["error_code"]]
    out.json("problems", problems, "¿Qué dispositivos tienen un error en el Administrador de dispositivos y cuál?")

    usb = [d for d in rows if (d["pnp_id"] or "").upper().startswith(("USB\\", "HID\\")) or d["class"] == "USB"]
    out.json("usb", usb, "¿Qué dispositivos USB y HID (mouse, teclado, joystick) hay conectados?")

    out.summary().update(
        count=len(rows),
        usb_count=len(usb),
        problem_devices=[d["name"] for d in problems],
    )


def _device(d: dict[str, Any]) -> dict[str, Any]:
    code = d.get("ConfigManagerErrorCode") or 0
    return {
        "name": d.get("Name"),
        "class": d.get("PNPClass"),
        "manufacturer": d.get("Manufacturer"),
        "status": d.get("Status"),
        "error_code": code,
        "error_meaning": ERROR_MEANINGS.get(code) if code else None,
        "pnp_id": d.get("PNPDeviceID"),
        "present": d.get("Present"),
    }
