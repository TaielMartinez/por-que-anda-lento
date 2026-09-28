"""Dominio gpu y su serie en la Ventana de muestreo."""

from conftest import fixture_ports

from lento.domains import gpu

MiB = 1024**2

NVIDIA_ROW = "NVIDIA GeForce RTX 3090, 591.86, P2, 71, 97, 40, 24576, 20000, 1890, 9501, 2115, 345.10, 370.00, 65, 0x0000000000000004, 4, 16"


def counters(engines: dict[str, float], memory: dict[str, float]):
    return {
        gpu.ENGINE: engines,
        gpu.PROCESS_MEMORY: memory,
        gpu.ADAPTER_MEMORY: {"luid_0x0_0xD0FF_phys_0": sum(memory.values())},
    }


def eng(pid: int, n: int, kind: str) -> str:
    return f"pid_{pid}_luid_0x00000000_0x0000D0FF_phys_0_eng_{n}_engtype_{kind}"


def mem(pid: int) -> str:
    return f"pid_{pid}_luid_0x00000000_0x0000D0FF_phys_0"


def scenario():
    ports = fixture_ports("gpu", "sampling")
    ports.set("run", gpu.NVIDIA_QUERY, 30, response={"returncode": 0, "stdout": NVIDIA_ROW + "\n", "stderr": ""})
    ports.set("counters", gpu.GPU_COUNTERS, response=counters(
        {eng(10, 0, "3D"): 60.0, eng(10, 1, "3D"): 30.0, eng(10, 5, "VideoDecode"): 20.0, eng(20, 0, "3D"): 5.0},
        {mem(10): 8000 * MiB, mem(20): 300 * MiB},
    ))
    ports.set("process_samples", response=[
        {"pid": 10, "name": "juego.exe"}, {"pid": 20, "name": "chrome.exe"},
    ])
    return ports


def test_real_gpu_snapshot_from_nvidia_smi(capture):
    cap = capture(fixture_ports("gpu"))

    adapters = cap.json("snapshot/gpu/adapters.json")
    assert adapters["source"] == "nvidia-smi"
    card = adapters["gpus"][0]
    assert "3090" in card["name"]
    assert card["memory_total_bytes"] == 24576 * MiB
    assert cap.domain("gpu")["status"] == "complete"


def test_throttle_reasons_are_decoded(capture):
    cap = capture(scenario())

    card = cap.json("snapshot/gpu/adapters.json")["gpus"][0]
    assert card["clock_event_reasons"] == ["sw_power_cap"]
    assert card["temperature_c"] == 71
    assert cap.summary["gpu"]["temperature_c"] == 71
    assert cap.summary["gpu"]["utilization_percent"] == 97


def test_per_process_usage_is_the_busiest_engine_type(capture):
    cap = capture(scenario())

    procs = cap.json("snapshot/gpu/processes.json")
    assert procs[0] == {
        "pid": 10, "name": "juego.exe", "gpu_percent": 90.0, "busiest_engine": "3D",
        "dedicated_memory_bytes": 8000 * MiB,
    }
    assert procs[1]["name"] == "chrome.exe"


def test_without_nvidia_smi_falls_back_to_counters_and_is_partial(capture):
    ports = scenario()
    ports.fail("run", gpu.NVIDIA_QUERY, 30, reason="comando no encontrado: nvidia-smi")

    cap = capture(ports)

    adapters = cap.json("snapshot/gpu/adapters.json")
    assert adapters["source"] == "counters"
    assert adapters["adapters"][0]["dedicated_memory_used_bytes"] == 8300 * MiB
    assert cap.entry("snapshot/gpu/adapters.json")["status"] == "partial"
    assert cap.json("snapshot/gpu/processes.json")[0]["gpu_percent"] == 90.0


def test_sampling_adds_gpu_series_and_top_gpu_processes(capture):
    cap = capture(scenario(), duration_s=2, interval_s=1)

    series = cap.csv("sampling/gpu.csv")
    assert len(series) == 3
    assert series[0]["utilization_percent"] == "97.0"
    top = cap.csv("sampling/processes_top_gpu.csv")
    assert [r["name"] for r in top if r["t_s"] == "1.0"] == ["juego.exe", "chrome.exe"]
    assert top[0]["rank"] == "1"
    assert cap.summary["sampling"]["gpu_utilization_percent"]["max"] == 97.0
    assert cap.summary["sampling"]["top_gpu_processes"][0]["name"] == "juego.exe"
