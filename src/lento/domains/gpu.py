"""Dominio gpu: estado de la placa de video y uso por proceso.

nvidia-smi da temperatura, clocks, consumo y motivos de limitación. Los contadores
`GPU Engine` / `GPU Process Memory` de Windows dan el uso por proceso para cualquier
fabricante, y sirven de respaldo cuando no hay NVIDIA.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Callable

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "gpu"
BASE = "snapshot/gpu"
DOC = "gpu"

TOP_N = 20

NVIDIA_FIELDS = [
    ("name", "name"),
    ("driver_version", "driver_version"),
    ("pstate", "pstate"),
    ("temperature_c", "temperature.gpu"),
    ("utilization_percent", "utilization.gpu"),
    ("memory_utilization_percent", "utilization.memory"),
    ("memory_total_mib", "memory.total"),
    ("memory_used_mib", "memory.used"),
    ("graphics_clock_mhz", "clocks.gr"),
    ("memory_clock_mhz", "clocks.mem"),
    ("max_graphics_clock_mhz", "clocks.max.gr"),
    ("power_draw_w", "power.draw"),
    ("power_limit_w", "power.limit"),
    ("fan_percent", "fan.speed"),
    ("clock_event_reasons_mask", "clocks_event_reasons.active"),
    ("pcie_gen", "pcie.link.gen.current"),
    ("pcie_width", "pcie.link.width.current"),
]
NVIDIA_QUERY = [
    "nvidia-smi",
    "--query-gpu=" + ",".join(f for _, f in NVIDIA_FIELDS),
    "--format=csv,noheader,nounits",
]
TEXT_FIELDS = {"name", "driver_version", "pstate", "clock_event_reasons_mask"}

# Bits de clocks_event_reasons (antes "throttle reasons") de NVML.
CLOCK_EVENT_REASONS = {
    0x1: "gpu_idle",
    0x2: "applications_clocks_setting",
    0x4: "sw_power_cap",
    0x8: "hw_slowdown",
    0x10: "sync_boost",
    0x20: "sw_thermal_slowdown",
    0x40: "hw_thermal_slowdown",
    0x80: "hw_power_brake_slowdown",
    0x100: "display_clock_setting",
}

ENGINE = "\\GPU Engine(*)\\Utilization Percentage"
PROCESS_MEMORY = "\\GPU Process Memory(*)\\Dedicated Usage"
ADAPTER_MEMORY = "\\GPU Adapter Memory(*)\\Dedicated Usage"
GPU_COUNTERS = [ENGINE, PROCESS_MEMORY, ADAPTER_MEMORY]

_ENGINE_INSTANCE = re.compile(r"pid_(\d+)_.*engtype_(.+)$")
_MEMORY_INSTANCE = re.compile(r"pid_(\d+)_")


def collect(ports: Ports, out: DomainWriter) -> None:
    cards, nvidia_error = read_nvidia(ports)
    counters = _counters(ports)
    if cards is not None:
        adapters: dict[str, Any] = {"source": "nvidia-smi", "gpus": cards}
        reason = None
    else:
        adapters = {
            "source": "counters",
            "adapters": [
                {"luid": luid, "dedicated_memory_used_bytes": _int(v)}
                for luid, v in (counters.get(ADAPTER_MEMORY) or {}).items()
            ],
        }
        reason = f"nvidia-smi no disponible ({nvidia_error}): solo contadores de Windows, sin temperatura ni clocks"
    out.json("adapters", adapters, "¿Qué uso, memoria, temperatura, clocks y limitaciones tiene la GPU?", reason)

    names = _names(ports)
    procs = [{"pid": pid, "name": names.get(pid), **usage} for pid, usage in per_process(counters).items()]
    procs.sort(key=lambda p: (p["gpu_percent"], p["dedicated_memory_bytes"]), reverse=True)
    out.json(
        "processes",
        procs,
        "¿Qué procesos usan la GPU, cuánto (motor más cargado) y cuánta memoria de video?",
        None if counters else "contadores de GPU no disponibles",
    )

    card = cards[0] if cards else {}
    out.summary().update(
        source=adapters["source"],
        name=card.get("name"),
        utilization_percent=card.get("utilization_percent"),
        temperature_c=card.get("temperature_c"),
        memory_used_bytes=card.get("memory_used_bytes"),
        memory_total_bytes=card.get("memory_total_bytes"),
        clock_event_reasons=card.get("clock_event_reasons"),
        top_processes=[{"name": p["name"], "gpu_percent": p["gpu_percent"]} for p in procs[:5]],
    )


def read_nvidia(ports: Ports) -> tuple[list[dict[str, Any]] | None, str | None]:
    try:
        result = ports.run(NVIDIA_QUERY, 30)
    except PortError as e:
        return None, str(e)
    if result["returncode"] != 0:
        return None, (result["stderr"] or result["stdout"]).strip()[:200]
    cards = [_card(line) for line in result["stdout"].splitlines() if line.strip()]
    return cards, None


def per_process(counters: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Por proceso: el tipo de motor más cargado (como el Administrador de tareas) y la VRAM dedicada."""
    by_type: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for instance, value in (counters.get(ENGINE) or {}).items():
        m = _ENGINE_INSTANCE.match(instance)
        if m and value:
            by_type[int(m.group(1))][m.group(2)] += value
    memory: dict[int, float] = defaultdict(float)
    for instance, value in (counters.get(PROCESS_MEMORY) or {}).items():
        m = _MEMORY_INSTANCE.match(instance)
        if m and value:
            memory[int(m.group(1))] += value
    result = {}
    for pid in set(by_type) | set(memory):
        engines = by_type.get(pid, {})
        busiest = max(engines, key=lambda k: engines[k], default=None)
        result[pid] = {
            "gpu_percent": round(min(engines[busiest], 100.0), 2) if busiest else 0.0,
            "busiest_engine": busiest,
            "dedicated_memory_bytes": int(memory.get(pid, 0)),
        }
    return result


class GpuSampler:
    """Serie de la GPU y top de procesos por GPU en cada muestra de la Ventana de muestreo."""

    COLUMNS = [
        "t_s", "utilization_percent", "memory_used_bytes", "temperature_c", "graphics_clock_mhz",
        "power_draw_w", "pstate", "clock_event_reasons",
    ]

    def __init__(self, ports: Ports, names: Callable[[], dict[int, str]]):
        self.ports = ports
        self.names = names
        self.nvidia = True
        self.series: list[dict[str, Any]] = []
        self.top: list[dict[str, Any]] = []
        self.per_process_rows: list[dict[str, Any]] = []
        self.reasons: list[str] = []

    def tick(self, t_s: float) -> None:
        row: dict[str, Any] = {"t_s": t_s}
        counters = _counters(self.ports)
        if self.nvidia:
            cards, error = read_nvidia(self.ports)
            if cards:
                c = cards[0]
                row.update({k: c[k] if k in TEXT_FIELDS else _float(c[k]) for k in self.COLUMNS if k in c and k != "clock_event_reasons"})
                row["clock_event_reasons"] = "|".join(c.get("clock_event_reasons") or [])
            else:
                self.nvidia = False
                self.reasons.append(f"nvidia-smi no disponible ({error}): serie solo con contadores")
        if not self.nvidia:
            usage = per_process(counters)
            row["utilization_percent"] = max((u["gpu_percent"] for u in usage.values()), default=None)
            row["memory_used_bytes"] = _int(sum((counters.get(ADAPTER_MEMORY) or {}).values())) if counters else None
        self.series.append(row)

        names = self.names()
        ranked = sorted(
            per_process(counters).items(),
            key=lambda kv: (kv[1]["gpu_percent"], kv[1]["dedicated_memory_bytes"]),
            reverse=True,
        )
        for rank, (pid, u) in enumerate(ranked[:TOP_N], start=1):
            self.top.append({"t_s": t_s, "rank": rank, "pid": pid, "name": names.get(pid), **u})
        for pid, u in ranked:
            self.per_process_rows.append({"pid": pid, "name": names.get(pid), **u})

    def finish(self, out: DomainWriter) -> None:
        out.csv(
            "gpu",
            self.series,
            "¿Cuánto se usó la GPU y a qué temperatura, clock y consumo estuvo en cada momento?",
            self.COLUMNS,
            "; ".join(self.reasons) or None,
        )
        out.csv(
            "processes_top_gpu",
            self.top,
            f"¿Cuáles fueron los {TOP_N} procesos que más usaron gpu en cada muestra? "
            "Criterio: % del motor de GPU más cargado, luego memoria de video dedicada.",
            ["t_s", "rank", "pid", "name", "gpu_percent", "busiest_engine", "dedicated_memory_bytes"],
        )
        from lento.domains.sampling import _stats, _top_by_mean

        summary = out.summary()
        summary["gpu_utilization_percent"] = _stats([r.get("utilization_percent") for r in self.series])
        summary["gpu_temperature_c"] = _stats([r.get("temperature_c") for r in self.series])
        summary["top_gpu_processes"] = _top_by_mean(self.per_process_rows, "gpu_percent")


def _card(line: str) -> dict[str, Any]:
    values = [v.strip() for v in line.split(",")]
    card: dict[str, Any] = {}
    for (key, _), raw in zip(NVIDIA_FIELDS, values):
        if raw in ("[N/A]", "N/A", "[Not Supported]", ""):
            card[key] = None
        elif key in TEXT_FIELDS:
            card[key] = raw
        else:
            number = float(raw)
            card[key] = int(number) if number.is_integer() else number
    if card.get("memory_total_mib") is not None:
        card["memory_total_bytes"] = int(card["memory_total_mib"]) * 1024 * 1024
    if card.get("memory_used_mib") is not None:
        card["memory_used_bytes"] = int(card["memory_used_mib"]) * 1024 * 1024
    mask = card.get("clock_event_reasons_mask")
    card["clock_event_reasons"] = _reasons(mask) if mask else None
    return card


def _reasons(mask: str) -> list[str]:
    try:
        value = int(mask, 16)
    except ValueError:
        return []
    return [name for bit, name in CLOCK_EVENT_REASONS.items() if value & bit]


def _counters(ports: Ports) -> dict[str, Any]:
    try:
        return ports.counters(GPU_COUNTERS)
    except PortError:
        return {}


def _names(ports: Ports) -> dict[int, str]:
    try:
        return {p["pid"]: p["name"] for p in ports.process_samples()}
    except PortError:
        return {}


def _float(value: Any) -> float | None:
    return None if value is None else round(float(value), 2)


def _int(value: Any) -> int | None:
    return None if value is None else int(value)
