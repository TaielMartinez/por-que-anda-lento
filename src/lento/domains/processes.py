"""Dominio processes: qué corre, cuánto consume y con qué línea de comando."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "processes"
BASE = "snapshot/processes"
DOC = "processes"


def collect(ports: Ports, out: DomainWriter) -> None:
    procs = ports.processes()
    inaccessible = [p for p in procs if p.get("private_bytes") is None]
    reason = (
        f"{len(inaccessible)} proceso(s) sin acceso a memoria/CPU (protegidos o terminados durante la lectura)"
        if inaccessible
        else None
    )

    rows = sorted((_row(p) for p in procs), key=lambda r: r["private_bytes"] or 0, reverse=True)
    out.json("list", rows, "¿Qué procesos corren y cuánta memoria, CPU, hilos y handles usa cada uno?", reason)

    out.json("tree", _tree(procs), "¿Qué proceso lanzó a cuál (árbol padre-hijo)?")

    cmdlines = [
        {"pid": p["pid"], "name": p["name"], "exe": p.get("exe"), "cmdline": _cmdline(p.get("cmdline"))}
        for p in procs
    ]
    out.json("cmdlines", cmdlines, "¿Con qué línea de comando y ejecutable se lanzó cada proceso?")

    io = sorted(
        (
            {
                "pid": p["pid"],
                "name": p["name"],
                "io_read_bytes": p.get("io_read_bytes"),
                "io_write_bytes": p.get("io_write_bytes"),
                "io_other_bytes": p.get("io_other_bytes"),
                "io_read_count": p.get("io_read_count"),
                "io_write_count": p.get("io_write_count"),
            }
            for p in procs
        ),
        key=lambda r: (r["io_read_bytes"] or 0) + (r["io_write_bytes"] or 0),
        reverse=True,
    )
    out.json("io", io, "¿Cuánto leyó y escribió cada proceso desde que arrancó?")

    handles = sorted(
        ({"pid": p["pid"], "name": p["name"], "num_handles": p.get("num_handles"), "num_threads": p.get("num_threads")}
         for p in procs),
        key=lambda r: r["num_handles"] or 0,
        reverse=True,
    )
    out.json("handles", handles, "¿Qué procesos tienen más handles e hilos abiertos (posibles fugas)?")

    out.summary().update(
        count=len(procs),
        private_bytes_total=sum(p.get("private_bytes") or 0 for p in procs),
        working_set_bytes_total=sum(p.get("working_set_bytes") or 0 for p in procs),
        threads_total=sum(p.get("num_threads") or 0 for p in procs),
        handles_total=sum(p.get("num_handles") or 0 for p in procs),
        inaccessible_count=len(inaccessible),
    )


def _row(p: dict[str, Any]) -> dict[str, Any]:
    user, system = p.get("cpu_user_s"), p.get("cpu_system_s")
    return {
        "pid": p["pid"],
        "ppid": p.get("ppid"),
        "name": p["name"],
        "username": p.get("username"),
        "started_at": _iso(p.get("create_time")),
        "status": p.get("status"),
        "priority": p.get("priority"),
        "cpu_s": round(user + system, 2) if user is not None and system is not None else None,
        "private_bytes": p.get("private_bytes"),
        "working_set_bytes": p.get("working_set_bytes"),
        "peak_working_set_bytes": p.get("peak_working_set_bytes"),
        "paged_pool_bytes": p.get("paged_pool_bytes"),
        "nonpaged_pool_bytes": p.get("nonpaged_pool_bytes"),
        "num_threads": p.get("num_threads"),
        "num_handles": p.get("num_handles"),
    }


def _tree(procs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = {p["pid"]: {"pid": p["pid"], "name": p["name"], "children": []} for p in procs}
    started = {p["pid"]: p.get("create_time") or 0 for p in procs}
    roots = []
    for p in sorted(procs, key=lambda p: p["pid"]):
        node = nodes[p["pid"]]
        ppid = p.get("ppid")
        parent = nodes.get(ppid)
        # Windows reutiliza PIDs: un "padre" que arrancó después que el hijo es otro proceso.
        if parent is not None and ppid != p["pid"] and started[ppid] <= started[p["pid"]]:
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots


def _cmdline(parts: list[str] | None) -> str | None:
    return subprocess.list2cmdline(parts) if parts else None


def _iso(ts: float | None) -> str | None:
    if not ts:  # procesos del kernel informan 0
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
