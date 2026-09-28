"""Historial: eventos de Windows de los últimos días, un archivo por fuente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "history"
BASE = "history"
DOC = "history"

DAYS = 7
MAX_EVENTS = 200


@dataclass(frozen=True)
class Source:
    name: str
    log: str
    filter: str  # condición XPath dentro de System[...]
    question: str


SOURCES = [
    Source(
        "disk",
        "System",
        "Provider[@Name='disk' or @Name='Ntfs' or @Name='stornvme' or @Name='storahci' or @Name='volmgr' "
        "or @Name='Microsoft-Windows-Ntfs'] and (Level=1 or Level=2 or Level=3)",
        "¿Hubo errores o advertencias de disco o del sistema de archivos?",
    ),
    Source(
        "whea",
        "System",
        "Provider[@Name='Microsoft-Windows-WHEA-Logger']",
        "¿Hubo errores de hardware reportados por WHEA (CPU, RAM, PCIe)?",
    ),
    Source(
        "resource_exhaustion",
        "System",
        "Provider[@Name='Microsoft-Windows-Resource-Exhaustion-Detector']",
        "¿Windows detectó que se quedaba sin memoria virtual?",
    ),
    Source(
        "diagnostics_performance",
        "Microsoft-Windows-Diagnostics-Performance/Operational",
        "(Level=1 or Level=2 or Level=3)",
        "¿Hubo arranques, apagados o suspensiones lentos, y qué los demoró?",
    ),
    Source(
        "gpu_tdr",
        "System",
        "(Provider[@Name='Display'] and EventID=4101) or Provider[@Name='nvlddmkm'] or Provider[@Name='amdkmdag']",
        "¿El driver de video dejó de responder y se reinició (TDR)?",
    ),
    Source(
        "unexpected_shutdowns",
        "System",
        "(Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=41) "
        "or (Provider[@Name='EventLog'] and EventID=6008)",
        "¿Hubo apagados o reinicios inesperados (cuelgues, cortes)?",
    ),
    Source(
        "app_crashes",
        "Application",
        "(Provider[@Name='Application Error'] and EventID=1000) "
        "or (Provider[@Name='Application Hang'] and EventID=1002)",
        "¿Qué aplicaciones se cerraron solas o se colgaron?",
    ),
]


def source_query(source: Source, days: int = DAYS) -> tuple[str, str]:
    ms = days * 24 * 3600 * 1000
    return source.log, f"*[System[({source.filter}) and TimeCreated[timediff(@SystemTime) <= {ms}]]]"


def collect(ports: Ports, out: DomainWriter) -> None:
    summary = out.summary()
    for source in SOURCES:
        log, xpath = source_query(source)
        reason = None
        try:
            events = ports.events(log, xpath, MAX_EVENTS)
        except PortError as e:
            events, reason = [], str(e)
        truncated = len(events) >= MAX_EVENTS
        out.json(
            source.name,
            {"log": log, "days": DAYS, "max_events": MAX_EVENTS, "truncated": truncated, "events": events},
            source.question,
            reason,
            note=f"truncado: se alcanzó el tope de {MAX_EVENTS} eventos (los más recientes)" if truncated else None,
        )
        summary[source.name] = _counts(events) if reason is None else {"total": None, "by_day": {}, "truncated": False}
        summary[source.name]["truncated"] = truncated


def _counts(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_day: dict[str, int] = {}
    for e in events:
        day = (e.get("time_created") or "")[:10]
        by_day[day] = by_day.get(day, 0) + 1
    return {"total": len(events), "by_day": dict(sorted(by_day.items()))}
