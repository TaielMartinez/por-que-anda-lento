"""Dominio thermals: temperaturas, ventiladores, clocks y consumo desde LibreHardwareMonitor."""

from __future__ import annotations

from statistics import mean
from typing import Any

from lento.capture import DomainWriter
from lento.ports import PortError, Ports

NAME = "thermals"
BASE = "snapshot/thermals"
DOC = "thermals"

UNITS = {"Temperature": "°C", "Clock": "MHz", "Fan": "RPM", "Power": "W", "Control": "%"}
SERIES_TYPES = ("Temperature", "Clock", "Fan", "Power")


def collect(ports: Ports, out: DomainWriter) -> None:
    sensors = [_row(s) for s in ports.sensors()]
    empty = [s for s in sensors if s["value"] is None]
    reason = (
        f"{len(empty)} sensor(es) sin valor (típico de la CPU y la placa sin el driver PawnIO o sin admin)"
        if empty
        else None
    )

    out.json("all_sensors", sensors, "¿Qué valor tiene cada sensor de hardware (todos los tipos)?", reason)
    for name, kinds, question in (
        ("temperatures", {"Temperature"}, "¿A qué temperatura están la CPU, la GPU, la placa y los discos?"),
        ("clocks", {"Clock"}, "¿A qué frecuencia corren los núcleos de la CPU, la GPU y la memoria?"),
        ("fans", {"Fan", "Control"}, "¿A qué velocidad giran los ventiladores?"),
        ("power", {"Power"}, "¿Cuánta potencia consumen la CPU y la GPU?"),
    ):
        rows = [s for s in sensors if s["type"] in kinds]
        missing = [s for s in rows if s["value"] is None]
        out.json(name, rows, question, f"{len(missing)} sensor(es) sin valor" if missing else None)

    package = next(
        (s["value"] for s in sensors if s["sensor"] == "CPU Package" and s["type"] == "Temperature"), None
    )
    out.summary().update(
        max_temperature_c_by_hardware=max_temperature_by_hardware([sensors]),
        cpu_package_c=package,
        cpu_average_clock_mhz=cpu_average_clock(sensors),
        sensors_without_value=len(empty),
    )


def max_temperature_by_hardware(readings: list[list[dict[str, Any]]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for sensors in readings:
        for s in sensors:
            if s["type"] != "Temperature" or s["value"] is None or "Distance to TjMax" in s["sensor"]:
                continue
            result[s["hardware"]] = round(max(result.get(s["hardware"], float("-inf")), s["value"]), 2)
    return dict(sorted(result.items()))


def cpu_average_clock(sensors: list[dict[str, Any]]) -> float | None:
    cores = [
        s["value"]
        for s in sensors
        if s["type"] == "Clock" and s["hardware_type"] == "Cpu" and s["sensor"].startswith("CPU Core #")
        and s["value"] is not None
    ]
    return round(mean(cores), 2) if cores else None


class ThermalSampler:
    """Serie de temperaturas, clocks, ventiladores y consumo durante la Ventana de muestreo."""

    def __init__(self, ports: Ports):
        self.ports = ports
        self.available = True
        self.reason: str | None = None
        self.readings: list[tuple[float, list[dict[str, Any]]]] = []

    def tick(self, t_s: float) -> None:
        if not self.available:
            return
        try:
            self.readings.append((t_s, [_row(s) for s in self.ports.sensors()]))
        except PortError as e:
            self.available = False
            self.reason = str(e)

    def finish(self, out: DomainWriter) -> None:
        columns: list[str] = []
        rows = []
        for t_s, sensors in self.readings:
            row: dict[str, Any] = {"t_s": t_s}
            for s in sensors:
                if s["type"] not in SERIES_TYPES:
                    continue
                column = f"{s['hardware']} / {s['sensor']} [{UNITS[s['type']]}]"
                if column not in columns:
                    columns.append(column)
                row[column] = None if s["value"] is None else round(float(s["value"]), 2)
            rows.append(row)
        out.csv(
            "thermals",
            rows,
            "¿Cómo evolucionaron temperaturas, clocks, ventiladores y consumo durante la Ventana?",
            ["t_s", *columns],
            self.reason,
        )
        from lento.domains.sampling import _stats

        summary = out.summary()
        summary["temperature_max_c_by_hardware"] = max_temperature_by_hardware([s for _, s in self.readings])
        summary["cpu_average_clock_mhz"] = _stats([cpu_average_clock(s) for _, s in self.readings], low=True)


def _row(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "hardware": s.get("hardware"),
        "hardware_type": s.get("hardware_type"),
        "parent": s.get("parent"),
        "sensor": s.get("sensor"),
        "type": s.get("type"),
        "unit": UNITS.get(s.get("type") or ""),
        "value": s.get("value"),
        "min": s.get("min"),
        "max": s.get("max"),
    }
