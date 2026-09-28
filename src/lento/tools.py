"""Herramientas externas que instala la Preparación (ADR 0003).

Cada herramienta tiene versión fijada, URL oficial y SHA256. Actualizar una herramienta
es cambiar a mano su `version`, `url` y `sha256` acá.
"""

from __future__ import annotations

import os
import winreg
from dataclasses import dataclass, field
from pathlib import Path

PROGRAM_FILES_X86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
KITS = PROGRAM_FILES_X86 / "Windows Kits" / "10"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    needed_for: str
    version: str
    url: str
    sha256: str
    filename: str
    # "zip": se extraen `extract` a tools/<folder>; "installer": se ejecuta con `install_args`.
    kind: str
    provides: str  # ruta (relativa a tools/ para zips, absoluta para instaladores) que prueba la instalación
    extract: list[str] = field(default_factory=list)
    folder: str = ""
    install_args: list[str] = field(default_factory=list)
    service: str | None = None  # para drivers: el servicio que prueba la instalación
    license: str = ""


TOOLS: list[Tool] = [
    Tool(
        name="librehardwaremonitor",
        description="LibreHardwareMonitor (biblioteca de sensores)",
        needed_for="temperaturas, ventiladores y clocks (dominio thermals)",
        version="0.9.6",
        url="https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.6/LibreHardwareMonitor.zip",
        sha256="086d9f1b5a99e643edc2cfaaac16051685b551e4c5ac0b32a57c58c0e529c001",
        filename="LibreHardwareMonitor-0.9.6.zip",
        kind="zip",
        folder="librehardwaremonitor",
        provides="librehardwaremonitor/LibreHardwareMonitorLib.dll",
        license="MPL 2.0",
    ),
    Tool(
        name="pawnio",
        description="PawnIO (driver que LibreHardwareMonitor usa para leer la CPU y la placa)",
        needed_for="temperaturas de CPU y placa (dominio thermals)",
        version="2.2.0",
        url="https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe",
        sha256="1f519a22e47187f70a1379a48ca604981c4fcf694f4e65b734aaa74a9fba3032",
        filename="PawnIO_setup-2.2.0.exe",
        kind="installer",
        install_args=["-install", "-silent"],
        provides="",
        service="PawnIO",
        license="GPL/LGPL (namazso)",
    ),
    Tool(
        name="autorunsc",
        description="Sysinternals Autoruns (consola)",
        needed_for="programas de inicio (dominio startup)",
        version="download.sysinternals.com (fijado por hash)",
        url="https://download.sysinternals.com/files/Autoruns.zip",
        sha256="7b3a8eed819f732a3e4c134aecaeaebb8d643a46490ccddb82cc8a1a745c4cf7",
        filename="Autoruns.zip",
        kind="zip",
        folder="sysinternals",
        extract=["autorunsc64.exe"],
        provides="sysinternals/autorunsc64.exe",
        license="Licencia de Sysinternals (se acepta con -accepteula)",
    ),
    Tool(
        name="sigcheck",
        description="Sysinternals Sigcheck",
        needed_for="firma y versión de drivers (dominio drivers)",
        version="download.sysinternals.com (fijado por hash)",
        url="https://download.sysinternals.com/files/Sigcheck.zip",
        sha256="b8a41256612b7d9c8821fb4d71e24d314c8f631118d076be601b7df90ef4cf7b",
        filename="Sigcheck.zip",
        kind="zip",
        folder="sysinternals",
        extract=["sigcheck64.exe"],
        provides="sysinternals/sigcheck64.exe",
        license="Licencia de Sysinternals (se acepta con -accepteula)",
    ),
    Tool(
        name="handle",
        description="Sysinternals Handle",
        needed_for="detalle de handles por tipo en procesos sospechosos de fugas",
        version="download.sysinternals.com (fijado por hash)",
        url="https://download.sysinternals.com/files/Handle.zip",
        sha256="279aaf8eccb6f79147f4dcc6ba091fb895c4cb8b199a0dd186a4c76bc519d2cd",
        filename="Handle.zip",
        kind="zip",
        folder="sysinternals",
        extract=["handle64.exe"],
        provides="sysinternals/handle64.exe",
        license="Licencia de Sysinternals (se acepta con -accepteula)",
    ),
    Tool(
        name="wpt",
        description="Windows Performance Toolkit (xperf) del Windows ADK 10.1.26100.9457",
        needed_for="latencia DPC/ISR por driver y red por proceso (traza ETW)",
        version="ADK 10.1.26100.9457 (septiembre 2026)",
        url="https://go.microsoft.com/fwlink/?linkid=2289980",
        sha256="ac6a930fdb5c2980ba5fefe606d47edaafcf5f647b4337411500d158ea77300f",
        filename="adksetup-10.1.26100.9457.exe",
        kind="installer",
        install_args=["/features", "OptionId.WindowsPerformanceToolkit", "/quiet", "/norestart", "/ceip", "off"],
        provides=str(KITS / "Windows Performance Toolkit" / "xperf.exe"),
        license="Licencia del Windows ADK (Microsoft)",
    ),
    Tool(
        name="pooltag",
        description="Debugging Tools for Windows (pooltag.txt) del Windows SDK 10.0.26100.9169",
        needed_for="traducir tags del pool del kernel a drivers (RAM no atribuida)",
        version="SDK 10.0.26100.9169 (agosto 2026)",
        url="https://go.microsoft.com/fwlink/?linkid=2376216",
        sha256="680aa29dcfa806d35b4e93ea05a3fa2bdcf2935b65295f996c8e944584dd2836",
        filename="winsdksetup-10.0.26100.9169.exe",
        kind="installer",
        install_args=["/features", "OptionId.WindowsDesktopDebuggers", "/quiet", "/norestart", "/ceip", "off"],
        provides=str(KITS / "Debuggers" / "x64" / "triage" / "pooltag.txt"),
        license="Licencia del Windows SDK (Microsoft)",
    ),
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def installed_path(name: str, tools_dir: Path) -> Path | None:
    """Ruta que prueba que la herramienta está instalada, o None."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return None
    if tool.service:
        return _service_path(tool.service)
    path = Path(tool.provides) if tool.kind == "installer" else tools_dir / tool.provides
    return path if path.exists() else None


def _service_path(service: str) -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\{service}") as key:
            image, _ = winreg.QueryValueEx(key, "ImagePath")
    except OSError:
        return None
    return Path(os.path.expandvars(str(image).replace("\\??\\", "")))
