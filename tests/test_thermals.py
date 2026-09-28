"""Dominio thermals (LibreHardwareMonitor) y su serie en la Ventana de muestreo."""

from conftest import fixture_ports

LHM = "C:\\tools\\librehardwaremonitor\\LibreHardwareMonitorLib.dll"


def sensor(hw, name, kind, value, hw_type="Cpu"):
    return {"hardware": hw, "hardware_type": hw_type, "parent": None, "sensor": name, "type": kind,
            "value": value, "min": value, "max": value, "id": f"/{hw}/{kind}/{name}"}


def reading(package_c, core_mhz, gpu_c=60.0):
    cpu = "Intel Core i7-8700K"
    return [
        sensor(cpu, "CPU Package", "Temperature", package_c),
        sensor(cpu, "CPU Core #1 Distance to TjMax", "Temperature", 100 - package_c),
        sensor(cpu, "CPU Core #1", "Clock", core_mhz),
        sensor(cpu, "CPU Core #2", "Clock", core_mhz),
        sensor(cpu, "CPU Total", "Load", 50.0),
        sensor("NVIDIA GeForce RTX 3090", "GPU Core", "Temperature", gpu_c, "GpuNvidia"),
        sensor("Z370 AORUS Ultra Gaming", "Fan #1", "Fan", 900.0, "SuperIO"),
    ]


def with_readings(*readings):
    ports = fixture_ports("thermals", "sampling")
    ports.set("tool_path", "librehardwaremonitor", response=LHM)
    ports.set_sequence("sensors", responses=list(readings))
    return ports


def test_real_sensors_with_cpu_values_missing_without_driver_are_partial(capture):
    cap = capture(fixture_ports("thermals"))

    temps = cap.json("snapshot/thermals/temperatures.json")
    gpu = [t for t in temps if t["hardware"] == "NVIDIA GeForce RTX 3090" and t["sensor"] == "GPU Core"]
    assert gpu and gpu[0]["value"] > 20
    entry = cap.entry("snapshot/thermals/temperatures.json")
    assert entry["status"] == "partial"
    assert "sin valor" in entry["reason"]
    assert cap.summary["thermals"]["max_temperature_c_by_hardware"]["NVIDIA GeForce RTX 3090"] > 20


def test_snapshot_groups_sensors_by_kind(capture):
    cap = capture(with_readings(reading(72.0, 4700.0)), only=["thermals"])

    temps = {t["sensor"]: t["value"] for t in cap.json("snapshot/thermals/temperatures.json")}
    assert temps["CPU Package"] == 72.0
    assert [c["sensor"] for c in cap.json("snapshot/thermals/clocks.json")] == ["CPU Core #1", "CPU Core #2"]
    assert cap.json("snapshot/thermals/fans.json")[0]["value"] == 900.0
    assert len(cap.json("snapshot/thermals/all_sensors.json")) == 7
    s = cap.summary["thermals"]
    assert s["max_temperature_c_by_hardware"] == {"Intel Core i7-8700K": 72.0, "NVIDIA GeForce RTX 3090": 60.0}
    assert s["cpu_package_c"] == 72.0


def test_without_librehardwaremonitor_thermals_fail_and_the_rest_continues(capture):
    ports = fixture_ports("thermals", "system")
    ports.set("tool_path", "librehardwaremonitor", response=None)
    ports.fail("sensors", reason="LibreHardwareMonitor no está instalado (correr la Preparación)")

    cap = capture(ports)

    assert cap.domain("thermals")["status"] == "failed"
    assert "Preparación" in cap.domain("thermals")["reasons"][0]
    assert cap.domain("system")["status"] == "complete"


def test_sampling_series_shows_heat_and_clock_drop(capture):
    ports = with_readings(reading(60.0, 4700.0), reading(95.0, 3000.0), reading(97.0, 2800.0))

    cap = capture(ports, duration_s=2, interval_s=1, only=["sampling"])

    rows = cap.csv("sampling/thermals.csv")
    assert len(rows) == 3
    assert rows[2]["Intel Core i7-8700K / CPU Package [°C]"] == "97.0"
    assert rows[2]["Intel Core i7-8700K / CPU Core #1 [MHz]"] == "2800.0"
    s = cap.summary["sampling"]
    assert s["temperature_max_c_by_hardware"]["Intel Core i7-8700K"] == 97.0
    assert s["cpu_average_clock_mhz"]["min"] == 2800.0


def test_sampling_without_sensors_writes_an_empty_partial_series(capture):
    ports = fixture_ports("sampling")
    ports.fail("sensors", reason="LibreHardwareMonitor no está instalado")

    cap = capture(ports, duration_s=1, interval_s=1, only=["sampling"])

    assert cap.entry("sampling/thermals.csv")["status"] == "partial"
    assert cap.exists("sampling/dpc_interrupt.csv")
