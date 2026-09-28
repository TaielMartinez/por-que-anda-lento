"""Ventana de muestreo: mide el sistema repetidamente durante un lapso configurable.

La ventana está hecha de *samplers*: cada uno lee algo en cada tick y al final escribe
sus CSV y su parte del Resumen. Los tickets siguientes agregan samplers (GPU,
temperaturas, traza ETW) sin tocar el bucle.
"""

from __future__ import annotations

import math
from statistics import mean
from typing import Any, Protocol

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "sampling"
BASE = "sampling"
DOC = "sampling"

TOP_N = 20

CPU_PER_CORE = ["\\Processor(*)\\% Processor Time"]

DPC_TIME = "\\Processor(_Total)\\% DPC Time"
INTERRUPT_TIME = "\\Processor(_Total)\\% Interrupt Time"
DPC_RATE = "\\Processor(_Total)\\DPC Rate"
INTERRUPTS = "\\Processor(_Total)\\Interrupts/sec"
DISK_QUEUE = "\\PhysicalDisk(_Total)\\Current Disk Queue Length"
DISK_AVG_QUEUE = "\\PhysicalDisk(_Total)\\Avg. Disk Queue Length"
DISK_TIME = "\\PhysicalDisk(_Total)\\% Disk Time"
DISK_BYTES = "\\PhysicalDisk(_Total)\\Disk Bytes/sec"
DISK_LATENCY = "\\PhysicalDisk(_Total)\\Avg. Disk sec/Transfer"
PAGE_READS = "\\Memory\\Page Reads/sec"
PAGES_INPUT = "\\Memory\\Pages Input/sec"
PAGE_FAULTS = "\\Memory\\Page Faults/sec"
AVAILABLE = "\\Memory\\Available Bytes"
COMMITTED = "\\Memory\\Committed Bytes"
PROCESSOR_QUEUE = "\\System\\Processor Queue Length"
CONTEXT_SWITCHES = "\\System\\Context Switches/sec"

SYSTEM_COUNTERS = [
    DPC_TIME, INTERRUPT_TIME, DPC_RATE, INTERRUPTS, DISK_QUEUE, DISK_AVG_QUEUE, DISK_TIME,
    DISK_BYTES, DISK_LATENCY, PAGE_READS, PAGES_INPUT, PAGE_FAULTS, AVAILABLE, COMMITTED,
    PROCESSOR_QUEUE, CONTEXT_SWITCHES,
]

# (archivo, pregunta, [(columna, contador)])
SYSTEM_FILES: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "dpc_interrupt",
        "¿Cuánto tiempo de CPU se fue en DPC e interrupciones de drivers en cada momento?",
        [("dpc_time_percent", DPC_TIME), ("interrupt_time_percent", INTERRUPT_TIME),
         ("dpc_rate", DPC_RATE), ("interrupts_per_s", INTERRUPTS)],
    ),
    (
        "disk",
        "¿Qué tan ocupado y lento estuvo el disco en cada momento?",
        [("current_queue_length", DISK_QUEUE), ("avg_queue_length", DISK_AVG_QUEUE),
         ("disk_time_percent", DISK_TIME), ("disk_bytes_per_s", DISK_BYTES),
         ("avg_sec_per_transfer", DISK_LATENCY)],
    ),
    (
        "page_faults",
        "¿Cuántas veces por segundo el sistema tuvo que leer memoria desde disco (hard page faults)?",
        [("page_reads_per_s", PAGE_READS), ("pages_input_per_s", PAGES_INPUT),
         ("page_faults_per_s", PAGE_FAULTS)],
    ),
    (
        "memory_available",
        "¿Cuánta RAM disponible y memoria comprometida hubo en cada momento?",
        [("available_bytes", AVAILABLE), ("committed_bytes", COMMITTED)],
    ),
    (
        "system_load",
        "¿Cuántos hilos esperaban CPU y cuántos cambios de contexto hubo en cada momento?",
        [("processor_queue_length", PROCESSOR_QUEUE), ("context_switches_per_s", CONTEXT_SWITCHES)],
    ),
]


class Sampler(Protocol):
    def tick(self, t_s: float) -> None: ...

    def finish(self, out: DomainWriter) -> None: ...


def collect(ports: Ports, out: DomainWriter) -> None:
    options = out.capture.options
    duration, interval = options.duration_s, options.interval_s
    ticks = max(1, math.floor(duration / interval + 1e-9))

    from lento.domains.gpu import GpuSampler

    cores = CpuCoreSampler(ports)
    processes = ProcessSampler(ports, cores.logical_processors)
    samplers: list[Sampler] = [
        cores,
        SystemCounterSampler(ports),
        processes,
        GpuSampler(ports, lambda: processes.names),
    ]

    start = ports.monotonic()
    for s in samplers:
        s.tick(0.0)
    for i in range(1, ticks + 1):
        t_s = round(ports.wait_until(start + i * interval) - start, 2)
        for s in samplers:
            s.tick(t_s)

    summary = out.summary()
    summary["samples"] = ticks + 1
    for s in samplers:
        s.finish(out)


class CpuCoreSampler:
    def __init__(self, ports: Ports):
        self.ports = ports
        self.rows: list[dict[str, Any]] = []
        first = ports.counters(CPU_PER_CORE)[CPU_PER_CORE[0]] or {}
        self.cores = sorted((k for k in first if k != "_Total"), key=_core_key)
        self.logical_processors = len(self.cores) or 1
        self._first: dict[str, Any] | None = first

    def tick(self, t_s: float) -> None:
        values = self._first if self._first is not None else self.ports.counters(CPU_PER_CORE)[CPU_PER_CORE[0]]
        self._first = None
        values = values or {}
        row: dict[str, Any] = {"t_s": t_s, "total_percent": _round(values.get("_Total"))}
        for core in self.cores:
            row[f"core{core}_percent"] = _round(values.get(core))
        self.rows.append(row)

    def finish(self, out: DomainWriter) -> None:
        columns = ["t_s", "total_percent", *(f"core{c}_percent" for c in self.cores)]
        out.csv("cpu_per_core", self.rows, "¿Cuánto se usó la CPU, en total y por núcleo, en cada momento?", columns)
        totals = [r["total_percent"] for r in self.rows]
        out.summary()["cpu_total_percent"] = _stats(totals)
        busiest = [max((r[c] or 0) for c in columns[2:]) if columns[2:] else None for r in self.rows]
        out.summary()["cpu_busiest_core_percent"] = _stats(busiest)


class SystemCounterSampler:
    def __init__(self, ports: Ports):
        self.ports = ports
        self.rows: list[dict[str, Any]] = []

    def tick(self, t_s: float) -> None:
        values = self.ports.counters(SYSTEM_COUNTERS)
        self.rows.append({"t_s": t_s, **values})

    def finish(self, out: DomainWriter) -> None:
        summary = out.summary()
        for name, question, columns in SYSTEM_FILES:
            rows = [{"t_s": r["t_s"], **{col: _round(r.get(counter)) for col, counter in columns}} for r in self.rows]
            missing = [col for col, _ in columns if all(r[col] is None for r in rows)]
            reason = f"contadores no disponibles: {', '.join(missing)}" if missing else None
            out.csv(name, rows, question, ["t_s", *(c for c, _ in columns)], reason)
        summary["dpc_time_percent"] = _stats([r.get(DPC_TIME) for r in self.rows])
        summary["interrupt_time_percent"] = _stats([r.get(INTERRUPT_TIME) for r in self.rows])
        summary["disk_queue_length"] = _stats([r.get(DISK_QUEUE) for r in self.rows])
        summary["disk_time_percent"] = _stats([r.get(DISK_TIME) for r in self.rows])
        summary["hard_page_reads_per_s"] = _stats([r.get(PAGE_READS) for r in self.rows])
        summary["available_bytes"] = _stats([r.get(AVAILABLE) for r in self.rows], low=True)


class ProcessSampler:
    """Tasas por proceso entre muestras consecutivas, más los tops por recurso."""

    TOPS = [
        ("cpu", "cpu_percent", "% de CPU (sobre el total de núcleos)",
         ["cpu_percent", "private_bytes", "working_set_bytes"]),
        ("ram", "private_bytes", "private bytes, con su crecimiento desde el inicio de la ventana",
         ["private_bytes", "private_bytes_delta", "working_set_bytes"]),
        ("disk", "io_total_bytes_per_s", "bytes de I/O por segundo (lectura + escritura)",
         ["io_read_bytes_per_s", "io_write_bytes_per_s", "io_total_bytes_per_s"]),
    ]

    def __init__(self, ports: Ports, logical_processors: int):
        self.ports = ports
        self.logical = logical_processors
        self.previous: tuple[float, dict[int, dict[str, Any]]] | None = None
        self.first_private: dict[int, int] = {}
        self.rows: list[dict[str, Any]] = []
        self.names: dict[int, str] = {}

    def tick(self, t_s: float) -> None:
        current = {p["pid"]: p for p in self.ports.process_samples()}
        self.names = {pid: p["name"] for pid, p in current.items()}
        for pid, p in current.items():
            if p.get("private_bytes") is not None:
                self.first_private.setdefault(pid, p["private_bytes"])
        if self.previous is not None:
            prev_t, prev = self.previous
            dt = t_s - prev_t
            for pid, p in current.items():
                self.rows.append(self._row(t_s, dt, p, prev.get(pid)))
        self.previous = (t_s, current)

    def _row(self, t_s: float, dt: float, p: dict[str, Any], before: dict[str, Any] | None) -> dict[str, Any]:
        def rate(field: str) -> float | None:
            if before is None or dt <= 0 or p.get(field) is None or before.get(field) is None:
                return None
            return max(0.0, (p[field] - before[field]) / dt)

        cpu = rate("cpu_s")
        read, write = rate("io_read_bytes"), rate("io_write_bytes")
        private = p.get("private_bytes")
        first = self.first_private.get(p["pid"])
        return {
            "t_s": t_s,
            "pid": p["pid"],
            "name": p["name"],
            "cpu_percent": _round(cpu * 100 / self.logical) if cpu is not None else None,
            "private_bytes": private,
            "private_bytes_delta": private - first if private is not None and first is not None else None,
            "working_set_bytes": p.get("working_set_bytes"),
            "io_read_bytes_per_s": _round(read),
            "io_write_bytes_per_s": _round(write),
            "io_total_bytes_per_s": _round(read + write) if read is not None and write is not None else None,
        }

    def finish(self, out: DomainWriter) -> None:
        all_columns = [
            "t_s", "pid", "name", "cpu_percent", "private_bytes", "private_bytes_delta",
            "working_set_bytes", "io_read_bytes_per_s", "io_write_bytes_per_s", "io_total_bytes_per_s",
        ]
        out.csv(
            "processes_all",
            self.rows,
            "¿Cuánta CPU, memoria e I/O usó cada proceso en cada muestra (todos los procesos)?",
            all_columns,
        )
        by_t: dict[float, list[dict[str, Any]]] = {}
        for r in self.rows:
            by_t.setdefault(r["t_s"], []).append(r)
        summary = out.summary()
        for resource, key, criterion, columns in self.TOPS:
            top_rows = []
            for t_s, rows in by_t.items():
                ranked = sorted((r for r in rows if r[key] is not None), key=lambda r: r[key], reverse=True)
                for rank, r in enumerate(ranked[:TOP_N], start=1):
                    top_rows.append({**r, "rank": rank})
            out.csv(
                f"processes_top_{resource}",
                top_rows,
                f"¿Cuáles fueron los {TOP_N} procesos que más usaron {resource} en cada muestra? "
                f"Criterio: {criterion}. Si un proceso no aparece, ver processes_all.",
                ["t_s", "rank", "pid", "name", *columns],
            )
            summary[f"top_{resource}_processes"] = _top_by_mean(self.rows, key)
        growth = [r for r in self.rows if r["private_bytes_delta"] is not None]
        last_t = max((r["t_s"] for r in growth), default=None)
        if last_t is not None:
            biggest = max((r for r in growth if r["t_s"] == last_t), key=lambda r: r["private_bytes_delta"])
            summary["largest_private_bytes_growth"] = {
                "pid": biggest["pid"], "name": biggest["name"], "private_bytes_delta": biggest["private_bytes_delta"],
            }


def _top_by_mean(rows: list[dict[str, Any]], key: str, n: int = 5) -> list[dict[str, Any]]:
    values: dict[tuple[int, str], list[float]] = {}
    for r in rows:
        if r[key] is not None:
            values.setdefault((r["pid"], r["name"]), []).append(r[key])
    ranked = sorted(values.items(), key=lambda kv: mean(kv[1]), reverse=True)[:n]
    return [{"pid": pid, "name": name, "mean": _round(mean(v)), "max": _round(max(v))} for (pid, name), v in ranked]


def _stats(values: list[Any], low: bool = False) -> dict[str, float | None]:
    """max, media y p95; para métricas donde lo malo es lo bajo (low), min, media y p5."""
    nums = sorted(float(v) for v in values if v is not None)
    if low:
        if not nums:
            return {"min": None, "mean": None, "p5": None}
        p5 = nums[max(0, math.ceil(0.05 * len(nums)) - 1)]
        return {"min": _round(nums[0]), "mean": _round(mean(nums)), "p5": _round(p5)}
    if not nums:
        return {"max": None, "mean": None, "p95": None}
    p95 = nums[min(len(nums) - 1, math.ceil(0.95 * len(nums)) - 1)]
    return {"max": _round(nums[-1]), "mean": _round(mean(nums)), "p95": _round(p95)}


def _round(value: Any) -> Any:
    return None if value is None else round(float(value), 2)


def _core_key(name: str) -> tuple[int, ...]:
    return tuple(int(x) for x in name.split(",") if x.isdigit())
