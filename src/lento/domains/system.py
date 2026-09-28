"""Dominio system: hardware, sistema operativo, plan de energía y ajustes gráficos."""

from __future__ import annotations

import re
from typing import Any

from lento.capture import DomainWriter
from lento.cim import iso, parse_cim_datetime, parse_iso
from lento.ports import PortError, Ports

NAME = "system"
BASE = "snapshot/system"
DOC = "system"

GRAPHICS_KEY = "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers"
GAMEBAR_KEY = "HKCU\\Software\\Microsoft\\GameBar"
POWER_OVERLAY_KEY = "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes"

# Overlays de "modo de energía" de Windows 11 (Configuración > Sistema > Energía).
POWER_OVERLAYS = {
    "961cc777-2547-4f9d-8174-7d86181b8a7a": "best_power_efficiency",
    "00000000-0000-0000-0000-000000000000": "balanced",
    "ded574b5-45a0-4f42-8737-46345c09c238": "best_performance",
}


def collect(ports: Ports, out: DomainWriter) -> None:
    hardware = _hardware(ports)
    out.json("hardware", hardware, "¿Qué CPU, RAM, placa, BIOS y GPU tiene la PC?")

    os_info = _os(ports)
    out.json("os", os_info, "¿Qué versión de Windows corre, desde cuándo está encendida y cómo está el archivo de paginación?")

    power, power_missing = _power(ports)
    out.json("power", power, "¿Qué plan y modo de energía están activos?", reason=power_missing)

    graphics, graphics_missing = _graphics(ports)
    out.json(
        "graphics_settings",
        graphics,
        "¿Están activos Game Mode y la programación de GPU acelerada por hardware (HAGS)?",
        reason=graphics_missing,
    )

    out.summary().update(
        cpu=hardware["cpu"]["name"],
        logical_processors=hardware["cpu"]["logical_processors"],
        ram_total_bytes=hardware["ram"]["total_bytes"],
        os_build=os_info["build"],
        uptime_hours=os_info["uptime_hours"],
        power_plan=power["active_plan"]["name"],
    )


def _hardware(ports: Ports) -> dict[str, Any]:
    cpu = ports.wmi(
        "SELECT Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed, "
        "L2CacheSize, L3CacheSize FROM Win32_Processor"
    )[0]
    cs = ports.wmi("SELECT Manufacturer, Model, TotalPhysicalMemory FROM Win32_ComputerSystem")[0]
    modules = ports.wmi(
        "SELECT Capacity, Speed, ConfiguredClockSpeed, Manufacturer, PartNumber, DeviceLocator, "
        "BankLabel FROM Win32_PhysicalMemory"
    )
    board = ports.wmi("SELECT Manufacturer, Product, Version FROM Win32_BaseBoard")
    bios = ports.wmi("SELECT Manufacturer, SMBIOSBIOSVersion, ReleaseDate FROM Win32_BIOS")
    gpus = ports.wmi(
        "SELECT Name, DriverVersion, DriverDate, AdapterRAM, CurrentHorizontalResolution, "
        "CurrentVerticalResolution, CurrentRefreshRate FROM Win32_VideoController"
    )
    return {
        "computer": {"manufacturer": cs.get("Manufacturer"), "model": cs.get("Model")},
        "cpu": {
            "name": (cpu.get("Name") or "").strip(),
            "cores": cpu.get("NumberOfCores"),
            "logical_processors": cpu.get("NumberOfLogicalProcessors"),
            "max_clock_mhz": cpu.get("MaxClockSpeed"),
            "current_clock_mhz": cpu.get("CurrentClockSpeed"),
            "l2_cache_kb": cpu.get("L2CacheSize"),
            "l3_cache_kb": cpu.get("L3CacheSize"),
        },
        "ram": {
            "total_bytes": _int(cs.get("TotalPhysicalMemory")),
            "modules": [
                {
                    "slot": m.get("DeviceLocator"),
                    "bank": m.get("BankLabel"),
                    "capacity_bytes": _int(m.get("Capacity")),
                    "speed_mhz": m.get("Speed"),
                    "configured_speed_mhz": m.get("ConfiguredClockSpeed"),
                    "manufacturer": (m.get("Manufacturer") or "").strip() or None,
                    "part_number": (m.get("PartNumber") or "").strip() or None,
                }
                for m in modules
            ],
        },
        "motherboard": {
            "manufacturer": board[0].get("Manufacturer") if board else None,
            "product": board[0].get("Product") if board else None,
            "version": board[0].get("Version") if board else None,
        },
        "bios": {
            "manufacturer": bios[0].get("Manufacturer") if bios else None,
            "version": bios[0].get("SMBIOSBIOSVersion") if bios else None,
            "release_date": iso(parse_cim_datetime(bios[0].get("ReleaseDate"))) if bios else None,
        },
        "gpus": [
            {
                "name": g.get("Name"),
                "driver_version": g.get("DriverVersion"),
                "driver_date": iso(parse_cim_datetime(g.get("DriverDate"))),
                "adapter_ram_bytes_wmi": _int(g.get("AdapterRAM")),
                "resolution": _resolution(g),
                "refresh_rate_hz": g.get("CurrentRefreshRate"),
            }
            for g in gpus
        ],
    }


def _os(ports: Ports) -> dict[str, Any]:
    os_row = ports.wmi(
        "SELECT Caption, Version, BuildNumber, OSArchitecture, LastBootUpTime, InstallDate "
        "FROM Win32_OperatingSystem"
    )[0]
    pagefiles = ports.wmi("SELECT Name, AllocatedBaseSize, CurrentUsage, PeakUsage FROM Win32_PageFileUsage")
    boot = parse_cim_datetime(os_row.get("LastBootUpTime"))
    now = parse_iso(ports.now())
    uptime = round((now - boot).total_seconds() / 3600, 2) if boot else None
    return {
        "caption": os_row.get("Caption"),
        "version": os_row.get("Version"),
        "build": str(os_row.get("BuildNumber")),
        "architecture": os_row.get("OSArchitecture"),
        "installed_at": iso(parse_cim_datetime(os_row.get("InstallDate"))),
        "last_boot_at": iso(boot),
        "uptime_hours": uptime,
        "pagefiles": [
            {
                "path": p.get("Name"),
                "allocated_mb": p.get("AllocatedBaseSize"),
                "current_usage_mb": p.get("CurrentUsage"),
                "peak_usage_mb": p.get("PeakUsage"),
            }
            for p in pagefiles
        ],
    }


_GUID = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def _power(ports: Ports) -> tuple[dict[str, Any], str | None]:
    result = ports.run(["powercfg", "/getactivescheme"])
    text = result["stdout"]
    guid = _GUID.search(text)
    name = re.search(r"\(([^)]*)\)\s*$", text.strip())
    power: dict[str, Any] = {
        "active_plan": {
            "guid": guid.group(1).lower() if guid else None,
            "name": name.group(1) if name else None,
        },
        "power_mode_overlay": None,
    }
    try:
        overlay = ports.registry_values(POWER_OVERLAY_KEY).get("ActiveOverlayAcPowerScheme")
        if overlay:
            power["power_mode_overlay"] = POWER_OVERLAYS.get(overlay.lower(), overlay)
    except PortError:
        pass  # solo existe en Windows 11 con modos de energía
    missing = None if guid else "no se pudo leer el plan activo"
    return power, missing


def _graphics(ports: Ports) -> tuple[dict[str, Any], str | None]:
    missing = []
    hags: bool | None = None
    try:
        mode = ports.registry_values(GRAPHICS_KEY).get("HwSchMode")
        hags = None if mode is None else mode == 2
    except PortError as e:
        missing.append(f"HAGS: {e}")

    game_mode: bool | None = None
    game_mode_default = False
    try:
        value = ports.registry_values(GAMEBAR_KEY).get("AutoGameModeEnabled")
        if value is None:
            game_mode, game_mode_default = True, True  # sin valor, Windows lo deja activo
        else:
            game_mode = value == 1
    except PortError as e:
        missing.append(f"Game Mode: {e}")

    return {
        "hardware_accelerated_gpu_scheduling": hags,
        "game_mode": game_mode,
        "game_mode_is_default": game_mode_default,
    }, "; ".join(missing) or None


def _resolution(g: dict[str, Any]) -> str | None:
    w, h = g.get("CurrentHorizontalResolution"), g.get("CurrentVerticalResolution")
    return f"{w}x{h}" if w and h else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
