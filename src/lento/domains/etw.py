"""Traza ETW del kernel durante la Ventana de muestreo: DPC/ISR por driver y red por proceso.

Graba con xperf (Windows Performance Toolkit, instalado por la Preparación) exactamente
mientras dura la Ventana y la procesa al terminar. Los resultados son archivos de la
Ventana de muestreo (`sampling/`).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

TOP_N = 20

_TOTAL = re.compile(r"Total\s*=\s*(\d+)\s+for module\s+(\S+)", re.IGNORECASE)
_BUCKET = re.compile(r"Elapsed Time,\s*>\s*(\d+)\s*usecs\s+AND\s+<=?\s*(\d+)\s*usecs,\s*(\d+)", re.IGNORECASE)
_PROCESS = re.compile(r"^(.*?)\s*\(\s*(\d+)\s*\)$")

DPC_COLUMNS = [
    "kind", "module", "count", "count_over_100us", "count_over_1ms", "max_usecs_bucket", "approx_total_usecs",
]


class EtwSampler:
    def __init__(self, ports: Ports, out: DomainWriter):
        self.ports = ports
        self.out = out
        self.keep = bool(getattr(out.capture.options, "keep_etl", False))
        self.ticks: list[float] = []
        self.xperf: str | None = None
        self.error: str | None = None
        self.started = False
        try:
            self.xperf = ports.tool_path("wpt")
        except PortError:
            self.xperf = None
        if not self.xperf:
            self.error = "WPT (xperf) no instalado: correr la Preparación para atribuir DPC/ISR y red a drivers y procesos"

    def tick(self, t_s: float) -> None:
        if not self.ticks and self.xperf:
            try:
                self.ports.etw_start(self.xperf)
                self.started = True
            except PortError as e:
                self.error = f"no se pudo iniciar la traza ETW: {e}"
        self.ticks.append(t_s)

    def finish(self, out: DomainWriter) -> None:
        result: dict[str, Any] = {}
        if self.started and self.xperf:
            try:
                result = self.ports.etw_stop(self.xperf, self.keep)
            except PortError as e:
                self.error = f"no se pudo procesar la traza ETW: {e}"
        out.capture.metadata["etw"] = {
            "trace": bool(result),
            "etl_kept": bool(result.get("etl")),
            "etl_path": result.get("etl"),
        }

        failed = not result
        dpc_rows = parse_dpcisr(result.get("dpcisr", "")) if result else []
        out.csv(
            "dpc_isr_by_driver",
            dpc_rows,
            "¿Qué drivers generaron DPC e interrupciones (ISR), cuántas y cuánto duraron?",
            DPC_COLUMNS,
            self.error,
            failed=failed,
        )
        interval = self.ticks[1] - self.ticks[0] if len(self.ticks) > 1 else 1.0
        net_rows = network_top(parse_network(result.get("network_dump", "")), self.ticks, interval) if result else []
        out.csv(
            "processes_top_net",
            net_rows,
            f"¿Cuáles fueron los {TOP_N} procesos que más usaron red en cada muestra? "
            "Criterio: bytes enviados + recibidos por segundo (TCP y UDP).",
            ["t_s", "rank", "pid", "name", "sent_bytes_per_s", "recv_bytes_per_s", "total_bytes_per_s"],
            self.error,
            failed=failed,
        )

        from lento.domains.sampling import _top_by_mean

        summary = out.summary()
        summary["dpc_isr_top_drivers"] = [
            {k: r[k] for k in ("kind", "module", "count", "count_over_1ms", "max_usecs_bucket", "approx_total_usecs")}
            for r in sorted(dpc_rows, key=lambda r: r["approx_total_usecs"], reverse=True)[:5]
        ]
        summary["top_net_processes"] = _top_by_mean(net_rows, "total_bytes_per_s")


def parse_dpcisr(text: str) -> list[dict[str, Any]]:
    """Histogramas por módulo de `xperf -a dpcisr`: secciones 'DPC' e 'Interrupt (ISR)'."""
    rows: list[dict[str, Any]] = []
    kind = "dpc"
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        header = line.strip().lower()
        if header.endswith("info"):
            kind = "isr" if ("interrupt" in header or "isr" in header) else "dpc"
            continue
        total = _TOTAL.search(line)
        if total:
            current = {
                "kind": kind, "module": total.group(2), "count": int(total.group(1)),
                "count_over_100us": 0, "count_over_1ms": 0, "max_usecs_bucket": 0, "approx_total_usecs": 0.0,
            }
            rows.append(current)
            continue
        bucket = _BUCKET.search(line)
        if bucket and current is not None:
            low, high, count = int(bucket.group(1)), int(bucket.group(2)), int(bucket.group(3))
            if count:
                current["max_usecs_bucket"] = max(current["max_usecs_bucket"], high)
                current["approx_total_usecs"] += count * (low + high) / 2
                if low >= 100:
                    current["count_over_100us"] += count
                if low >= 1000:
                    current["count_over_1ms"] += count
    for r in rows:
        r["approx_total_usecs"] = round(r["approx_total_usecs"], 1)
    return rows


def parse_network(dump: str) -> list[dict[str, Any]]:
    """Eventos TcpIp/UdpIp Send/Recv del volcado de xperf: tiempo (s), proceso, dirección y bytes."""
    columns: dict[str, list[str]] = {}
    events: list[dict[str, Any]] = []
    in_header = False
    for line in dump.splitlines():
        stripped = line.strip()
        if stripped == "BeginHeader":
            in_header = True
            continue
        if stripped == "EndHeader":
            in_header = False
            continue
        parts = [p.strip() for p in stripped.split(",")]
        if in_header:
            columns[parts[0]] = [c.lower() for c in parts]
            continue
        name = parts[0]
        direction = "sent" if "Send" in name else "recv" if "Recv" in name else None
        header = columns.get(name)
        if direction is None or header is None or len(parts) != len(header):
            continue
        row = dict(zip(header, parts))
        process = _PROCESS.match(row.get("process name ( pid)", ""))
        try:
            size = int(row["size"])
            t = int(row["timestamp"]) / 1_000_000
        except (KeyError, ValueError):
            continue
        events.append({
            "t": t,
            "pid": int(process.group(2)) if process else None,
            "name": process.group(1) if process else None,
            "direction": direction,
            "bytes": size,
        })
    return events


def network_top(events: list[dict[str, Any]], ticks: list[float], interval: float) -> list[dict[str, Any]]:
    """Asigna cada evento a la muestra que lo cierra (t_{i-1}, t_i] y rankea por proceso."""
    buckets: dict[float, dict[tuple[Any, Any], dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"sent": 0.0, "recv": 0.0})
    )
    for e in events:
        t_s = next((t for t in ticks[1:] if e["t"] <= t), None)
        if t_s is None:
            continue
        buckets[t_s][(e["pid"], e["name"])][e["direction"]] += e["bytes"]
    rows = []
    for t_s in ticks[1:]:
        ranked = sorted(buckets.get(t_s, {}).items(), key=lambda kv: kv[1]["sent"] + kv[1]["recv"], reverse=True)
        for rank, ((pid, name), b) in enumerate(ranked[:TOP_N], start=1):
            rows.append({
                "t_s": t_s, "rank": rank, "pid": pid, "name": name,
                "sent_bytes_per_s": round(b["sent"] / interval, 2),
                "recv_bytes_per_s": round(b["recv"] / interval, 2),
                "total_bytes_per_s": round((b["sent"] + b["recv"]) / interval, 2),
            })
    return rows
