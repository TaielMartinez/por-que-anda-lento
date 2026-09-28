"""Dominio memory: totales, listas de páginas, compresión, pool del kernel y RAM no atribuida."""

from __future__ import annotations

from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "memory"
BASE = "snapshot/memory"
DOC = "memory"

AVAILABLE = "\\Memory\\Available Bytes"
COMMITTED = "\\Memory\\Committed Bytes"
COMMIT_LIMIT = "\\Memory\\Commit Limit"
CACHE = "\\Memory\\Cache Bytes"
POOL_NONPAGED = "\\Memory\\Pool Nonpaged Bytes"
POOL_PAGED = "\\Memory\\Pool Paged Bytes"
POOL_PAGED_RESIDENT = "\\Memory\\Pool Paged Resident Bytes"
CACHE_RESIDENT = "\\Memory\\System Cache Resident Bytes"
CODE_RESIDENT = "\\Memory\\System Code Resident Bytes"
DRIVER_RESIDENT = "\\Memory\\System Driver Resident Bytes"
STANDBY_CORE = "\\Memory\\Standby Cache Core Bytes"
STANDBY_NORMAL = "\\Memory\\Standby Cache Normal Priority Bytes"
STANDBY_RESERVE = "\\Memory\\Standby Cache Reserve Bytes"
MODIFIED = "\\Memory\\Modified Page List Bytes"
FREE_ZERO = "\\Memory\\Free & Zero Page List Bytes"
PRIVATE_WS_TOTAL = "\\Process(_Total)\\Working Set - Private"
COMPRESSION_WS = "\\Process(Memory Compression)\\Working Set"

COUNTERS = [
    AVAILABLE, COMMITTED, COMMIT_LIMIT, CACHE, POOL_NONPAGED, POOL_PAGED, POOL_PAGED_RESIDENT,
    CACHE_RESIDENT, CODE_RESIDENT, DRIVER_RESIDENT, STANDBY_CORE, STANDBY_NORMAL, STANDBY_RESERVE,
    MODIFIED, FREE_ZERO, PRIVATE_WS_TOTAL, COMPRESSION_WS,
]

TOP_TAGS_IN_SUMMARY = 5


def collect(ports: Ports, out: DomainWriter) -> None:
    info = ports.performance_info()
    c = {k: _int(v) for k, v in ports.counters(COUNTERS).items()}

    total = info["physical_total_bytes"]
    available = c.get(AVAILABLE)
    if available is None:
        available = info["physical_available_bytes"]
    used = total - available

    totals = {
        "physical_total_bytes": total,
        "physical_available_bytes": available,
        "physical_used_bytes": used,
        "commit_total_bytes": _or(c.get(COMMITTED), info["commit_total_bytes"]),
        "commit_limit_bytes": _or(c.get(COMMIT_LIMIT), info["commit_limit_bytes"]),
        "commit_peak_bytes": info["commit_peak_bytes"],
        "cache_bytes": c.get(CACHE),
        "paged_pool_bytes": c.get(POOL_PAGED),
        "nonpaged_pool_bytes": c.get(POOL_NONPAGED),
        "handle_count": info["handle_count"],
        "process_count": info["process_count"],
        "thread_count": info["thread_count"],
    }
    out.json("totals", totals, "¿Cuánta RAM y memoria comprometida se usa en total?", _missing(totals))

    standby = {
        "core_bytes": c.get(STANDBY_CORE),
        "normal_priority_bytes": c.get(STANDBY_NORMAL),
        "reserve_bytes": c.get(STANDBY_RESERVE),
    }
    lists = {
        "standby_bytes": _sum(standby.values()),
        "standby": standby,
        "modified_bytes": c.get(MODIFIED),
        "free_and_zero_bytes": c.get(FREE_ZERO),
    }
    out.json(
        "page_lists",
        lists,
        "¿Cuánta RAM está en standby (caché reutilizable), modificada o libre?",
        _missing({**standby, "modified_bytes": lists["modified_bytes"], "free_and_zero_bytes": lists["free_and_zero_bytes"]}),
    )

    compression = {"compression_store_bytes": c.get(COMPRESSION_WS)}
    out.json(
        "compression",
        compression,
        "¿Cuánta RAM ocupa el almacén de memoria comprimida?",
        _missing(compression),
    )

    pool_reason = None
    try:
        tags = _pool_tags(ports.pool_tags())
    except PortError as e:
        tags, pool_reason = [], str(e)
    out.json("pool_tags", tags, "¿Qué tags del pool del kernel ocupan más memoria?", pool_reason)

    attribution = _attribution(used, c)
    out.json(
        "attribution",
        attribution,
        "¿Cuánta RAM usada no se atribuye a ningún proceso y en qué se descompone?",
        _missing(attribution["breakdown"]),
    )

    out.summary().update(
        total_bytes=total,
        used_bytes=used,
        available_bytes=available,
        used_percent=round(used / total * 100, 1) if total else None,
        commit_percent=_pct(totals["commit_total_bytes"], totals["commit_limit_bytes"]),
        standby_bytes=lists["standby_bytes"],
        processes_private_working_set_bytes=attribution["processes_private_working_set_bytes"],
        unattributed_to_processes_bytes=attribution["unattributed_to_processes_bytes"],
        unattributed_breakdown=attribution["breakdown"],
        top_nonpaged_pool_tags=[
            {"tag": t["tag"], "nonpaged_bytes": t["nonpaged_bytes"]}
            for t in tags[:TOP_TAGS_IN_SUMMARY]
        ],
    )


def _attribution(used: int, c: dict[str, int | None]) -> dict[str, Any]:
    compression = c.get(COMPRESSION_WS)
    private_total = c.get(PRIVATE_WS_TOTAL)
    in_processes = None
    if private_total is not None:
        in_processes = private_total - (compression or 0)
    unattributed = used - in_processes if in_processes is not None else None
    breakdown: dict[str, int | None] = {
        "nonpaged_pool_bytes": c.get(POOL_NONPAGED),
        "paged_pool_resident_bytes": c.get(POOL_PAGED_RESIDENT),
        "system_cache_resident_bytes": c.get(CACHE_RESIDENT),
        "system_driver_resident_bytes": c.get(DRIVER_RESIDENT),
        "system_code_resident_bytes": c.get(CODE_RESIDENT),
        "compression_store_bytes": compression,
        "modified_page_list_bytes": c.get(MODIFIED),
    }
    known = [v for v in breakdown.values() if v is not None]
    breakdown["unexplained_bytes"] = unattributed - sum(known) if unattributed is not None else None
    return {
        "used_bytes": used,
        "processes_private_working_set_bytes": in_processes,
        "unattributed_to_processes_bytes": unattributed,
        "breakdown": breakdown,
    }


def _pool_tags(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "tag": t["tag"],
            "nonpaged_bytes": t["nonpaged_bytes"],
            "paged_bytes": t["paged_bytes"],
            "nonpaged_outstanding_allocs": t["nonpaged_allocs"] - t["nonpaged_frees"],
            "paged_outstanding_allocs": t["paged_allocs"] - t["paged_frees"],
        }
        for t in raw
        if t["nonpaged_bytes"] or t["paged_bytes"]
    ]
    return sorted(rows, key=lambda r: (r["nonpaged_bytes"], r["paged_bytes"]), reverse=True)


def _missing(values: dict[str, Any]) -> str | None:
    missing = [k for k, v in values.items() if v is None]
    return f"contadores no disponibles: {', '.join(missing)}" if missing else None


def _sum(values: Any) -> int | None:
    values = list(values)
    return None if any(v is None for v in values) else sum(values)


def _pct(part: int | None, whole: int | None) -> float | None:
    return round(part / whole * 100, 1) if part is not None and whole else None


def _or(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def _int(value: Any) -> int | None:
    return None if value is None else int(value)
