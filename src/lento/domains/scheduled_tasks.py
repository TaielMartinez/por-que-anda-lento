"""Dominio scheduled_tasks: tareas programadas habilitadas y cuáles corrieron hace poco."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from lento.capture import DomainWriter
from lento.cim import parse_iso
from lento.ports import Ports

NAME = "scheduled_tasks"
BASE = "snapshot/scheduled_tasks"
DOC = "scheduled_tasks"

SCRIPT = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' } | ForEach-Object {
  $i = $_ | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue
  [pscustomobject]@{
    path = $_.TaskPath; name = $_.TaskName; state = [string]$_.State; author = $_.Author
    actions = @($_.Actions | ForEach-Object { ((@($_.Execute, $_.Arguments) | Where-Object { $_ }) -join ' ') })
    triggers = @($_.Triggers | ForEach-Object { $_.CimClass.CimClassName })
    last_run = $(if ($i -and $i.LastRunTime -and $i.LastRunTime.Year -gt 2000) { $i.LastRunTime.ToString('yyyy-MM-ddTHH:mm:sszzz') })
    next_run = $(if ($i -and $i.NextRunTime) { $i.NextRunTime.ToString('yyyy-MM-ddTHH:mm:sszzz') })
    last_result = $(if ($i) { $i.LastTaskResult })
  }
} | ConvertTo-Json -Depth 3 -Compress
"""
COMMAND = ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT]


def collect(ports: Ports, out: DomainWriter) -> None:
    result = ports.run(COMMAND, 300)
    reason = None
    try:
        data = json.loads(result["stdout"] or "[]")
    except json.JSONDecodeError:
        data, reason = [], f"no se pudo leer la salida de PowerShell: {result['stderr'][:200]}"
    tasks: list[dict[str, Any]] = [data] if isinstance(data, dict) else data
    for t in tasks:
        t["full_path"] = f"{t.get('path') or ''}{t.get('name') or ''}"
    tasks.sort(key=lambda t: t["full_path"].lower())

    out.json("enabled", tasks, "¿Qué tareas programadas están habilitadas, qué ejecutan y cuándo corrieron?", reason)
    third_party = [t for t in tasks if not (t.get("path") or "").startswith("\\Microsoft\\")]
    out.json("third_party", third_party, "¿Qué tareas programadas habilitadas no son de Windows?", reason)

    now = parse_iso(ports.now())
    recent = [
        t["full_path"]
        for t in tasks
        if t.get("last_run") and now - timedelta(hours=1) <= parse_iso(t["last_run"]) <= now
    ]
    out.summary().update(
        enabled_count=len(tasks),
        third_party=[t["full_path"] for t in third_party],
        running=[t["full_path"] for t in tasks if t.get("state") == "Running"],
        ran_last_hour=recent,
    )
