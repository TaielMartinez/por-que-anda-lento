"""Dominio system: hardware, OS, energía y ajustes gráficos."""

from conftest import fixture_ports

GiB = 1024**3


def test_hardware_describes_cpu_ram_and_gpu(capture):
    cap = capture(fixture_ports("system"))

    hw = cap.json("snapshot/system/hardware.json")
    assert "i7-8700K" in hw["cpu"]["name"]
    assert hw["cpu"]["logical_processors"] == 12
    assert hw["cpu"]["cores"] == 6
    assert 23 * GiB < hw["ram"]["total_bytes"] <= 24 * GiB
    assert sum(m["capacity_bytes"] for m in hw["ram"]["modules"]) == 24 * GiB
    assert any("3090" in g["name"] for g in hw["gpus"])


def test_os_reports_build_and_uptime(capture):
    cap = capture(fixture_ports("system"))

    os_info = cap.json("snapshot/system/os.json")
    assert os_info["build"] == "26200"
    assert os_info["uptime_hours"] > 0
    assert cap.summary["system"]["uptime_hours"] == os_info["uptime_hours"]


def test_power_plan_and_graphics_settings(capture):
    cap = capture(fixture_ports("system"))

    power = cap.json("snapshot/system/power.json")
    assert power["active_plan"]["name"]
    graphics = cap.json("snapshot/system/graphics_settings.json")
    assert graphics["hardware_accelerated_gpu_scheduling"] in (True, False, None)
    assert graphics["game_mode"] in (True, False, None)
    assert cap.domain("system")["status"] == "complete"


def test_missing_registry_values_make_the_domain_partial(capture):
    ports = fixture_ports("system")
    ports.fail("registry_values", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers")

    cap = capture(ports)

    graphics = cap.json("snapshot/system/graphics_settings.json")
    assert graphics["hardware_accelerated_gpu_scheduling"] is None
    assert cap.entry("snapshot/system/graphics_settings.json")["status"] == "partial"
    assert cap.domain("system")["status"] == "partial"
