"""Lectura de sensores con LibreHardwareMonitorLib desde PowerShell (.NET Framework).

Abrir la biblioteca tarda segundos, así que el lector queda vivo como un proceso de
PowerShell que devuelve una lectura por cada línea que recibe en stdin. Parte del
adaptador real; se valida con la prueba de humo.
"""

from __future__ import annotations

import atexit
import json
import subprocess
from pathlib import Path
from typing import Any

SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -Path $env:LHM_DLL
$c = New-Object LibreHardwareMonitor.Hardware.Computer
$c.IsCpuEnabled = $true; $c.IsGpuEnabled = $true; $c.IsMotherboardEnabled = $true
$c.IsStorageEnabled = $true; $c.IsMemoryEnabled = $true; $c.IsControllerEnabled = $true
$c.Open()
function Read-Hw($hw, $parent) {
  $hw.Update()
  foreach ($s in $hw.Sensors) {
    [pscustomobject]@{
      hardware = $hw.Name; hardware_type = [string]$hw.HardwareType; parent = $parent
      sensor = $s.Name; type = [string]$s.SensorType; value = $s.Value; min = $s.Min; max = $s.Max
      id = [string]$s.Identifier
    }
  }
  foreach ($sub in $hw.SubHardware) { Read-Hw $sub $hw.Name }
}
while ($null -ne ($line = [Console]::In.ReadLine())) {
  $rows = @(foreach ($hw in $c.Hardware) { Read-Hw $hw $null })
  [Console]::Out.WriteLine((ConvertTo-Json -InputObject $rows -Compress -Depth 3))
  [Console]::Out.Flush()
}
$c.Close()
"""

_readers: dict[Path, subprocess.Popen[str]] = {}


def read_sensors(dll: Path) -> list[dict[str, Any]]:
    proc = _readers.get(dll)
    if proc is None or proc.poll() is not None:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env={**__import__("os").environ, "LHM_DLL": str(dll)},
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _readers[dll] = proc
    assert proc.stdin and proc.stdout
    proc.stdin.write("read\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        error = proc.stderr.read() if proc.stderr else ""
        _readers.pop(dll, None)
        raise RuntimeError(f"LibreHardwareMonitor no respondió: {error.strip()[:300]}")
    data = json.loads(line)
    return data if isinstance(data, list) else [data]


@atexit.register
def _close() -> None:
    for proc in _readers.values():
        if proc.stdin:
            proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
