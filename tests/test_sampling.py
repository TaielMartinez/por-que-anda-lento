"""Ventana de muestreo: series temporales del sistema y de procesos."""

from conftest import fixture_ports

from lento.domains.sampling import CPU_PER_CORE, SYSTEM_COUNTERS

MiB = 1024**2


def proc(pid, name, cpu_s=0.0, private=100 * MiB, ws=50 * MiB, read=0, write=0):
    return {"pid": pid, "name": name, "cpu_s": cpu_s, "private_bytes": private,
            "working_set_bytes": ws, "io_read_bytes": read, "io_write_bytes": write}


def counters(dpc=1.0, interrupt=0.5, queue=0.0, page_reads=0.0, available=8 * 1024 * MiB):
    return {
        "\\Processor(_Total)\\% DPC Time": dpc,
        "\\Processor(_Total)\\% Interrupt Time": interrupt,
        "\\Processor(_Total)\\DPC Rate": 3.0,
        "\\Processor(_Total)\\Interrupts/sec": 5000.0,
        "\\PhysicalDisk(_Total)\\Current Disk Queue Length": queue,
        "\\PhysicalDisk(_Total)\\Avg. Disk Queue Length": queue,
        "\\PhysicalDisk(_Total)\\% Disk Time": 10.0,
        "\\PhysicalDisk(_Total)\\Disk Bytes/sec": 1000.0,
        "\\PhysicalDisk(_Total)\\Avg. Disk sec/Transfer": 0.001,
        "\\Memory\\Page Reads/sec": page_reads,
        "\\Memory\\Pages Input/sec": page_reads * 4,
        "\\Memory\\Page Faults/sec": 1000.0,
        "\\Memory\\Available Bytes": available,
        "\\Memory\\Committed Bytes": 16 * 1024 * MiB,
        "\\System\\Processor Queue Length": 1.0,
        "\\System\\Context Switches/sec": 20000.0,
    }


def scenario(process_ticks, counter_ticks=None, cores=4):
    """Muestras fabricadas: una respuesta por tick, un segundo entre ticks."""
    ports = fixture_ports("sampling")
    n = len(process_ticks)
    ports.set_sequence("monotonic", responses=[float(i) for i in range(n)])
    ports.set_sequence("process_samples", responses=process_ticks)
    ports.set_sequence("counters", SYSTEM_COUNTERS, responses=counter_ticks or [counters()] * n)
    per_core = {str(i): 10.0 * (i + 1) for i in range(cores)} | {"_Total": 25.0}
    ports.set("counters", CPU_PER_CORE, response={CPU_PER_CORE[0]: per_core})
    return ports


def test_one_csv_per_metric_for_the_whole_window(capture):
    cap = capture(fixture_ports("sampling"), duration_s=3, interval_s=1)

    for name in ("cpu_per_core", "dpc_interrupt", "disk", "page_faults", "memory_available", "system_load"):
        rows = cap.csv(f"sampling/{name}.csv")
        assert len(rows) == 4, name  # muestra inicial + 3 ticks
        assert rows[0]["t_s"] == "0.0"
    assert cap.manifest["sampling"] == {"duration_s": 3, "interval_s": 1}
    assert cap.domain("sampling")["status"] == "complete"


def test_duration_and_interval_decide_the_number_of_samples(capture):
    cap = capture(fixture_ports("sampling"), duration_s=10, interval_s=2)

    assert len(cap.csv("sampling/dpc_interrupt.csv")) == 6


def test_process_rates_are_computed_between_samples(capture):
    ticks = [
        [proc(10, "a.exe", cpu_s=1.0, read=0, write=0)],
        [proc(10, "a.exe", cpu_s=1.5, read=4 * MiB, write=2 * MiB)],
    ]
    cap = capture(scenario(ticks, cores=4), duration_s=1, interval_s=1)

    rows = cap.csv("sampling/processes_all.csv")
    assert len(rows) == 1
    row = rows[0]
    # 0.5 s de CPU en 1 s = 50 % de un núcleo = 12.5 % del total con 4 núcleos
    assert float(row["cpu_percent"]) == 12.5
    assert float(row["io_read_bytes_per_s"]) == 4 * MiB
    assert float(row["io_write_bytes_per_s"]) == 2 * MiB


def test_top_ram_reports_growth_since_the_window_started(capture):
    ticks = [
        [proc(10, "fuga.exe", private=100 * MiB), proc(20, "estable.exe", private=500 * MiB)],
        [proc(10, "fuga.exe", private=250 * MiB), proc(20, "estable.exe", private=500 * MiB)],
        [proc(10, "fuga.exe", private=400 * MiB), proc(20, "estable.exe", private=500 * MiB)],
    ]
    cap = capture(scenario(ticks), duration_s=2, interval_s=1)

    last = [r for r in cap.csv("sampling/processes_top_ram.csv") if r["t_s"] == "2.0"]
    assert [r["name"] for r in last] == ["estable.exe", "fuga.exe"]
    assert int(last[1]["private_bytes_delta"]) == 300 * MiB
    assert int(last[0]["private_bytes_delta"]) == 0
    assert cap.summary["sampling"]["largest_private_bytes_growth"] == {
        "pid": 10, "name": "fuga.exe", "private_bytes_delta": 300 * MiB,
    }


def test_each_top_keeps_at_most_20_processes_per_sample_and_all_keeps_everyone(capture):
    before = [proc(i, f"p{i}.exe", cpu_s=0.0) for i in range(25)]
    after = [proc(i, f"p{i}.exe", cpu_s=i / 100, read=i * MiB) for i in range(25)]
    cap = capture(scenario([before, after]), duration_s=1, interval_s=1)

    assert len(cap.csv("sampling/processes_all.csv")) == 25
    for resource in ("cpu", "ram", "disk"):
        rows = cap.csv(f"sampling/processes_top_{resource}.csv")
        assert len(rows) == 20, resource
        assert rows[0]["rank"] == "1"
    top_cpu = cap.csv("sampling/processes_top_cpu.csv")
    assert top_cpu[0]["name"] == "p24.exe"
    assert "20" in cap.entry("sampling/processes_top_cpu.csv")["question"]


def test_summary_has_peaks_and_means(capture):
    ticks = [[proc(1, "a.exe")]] * 4
    counter_ticks = [counters(dpc=1.0), counters(dpc=9.0), counters(dpc=2.0), counters(dpc=4.0)]
    cap = capture(scenario(ticks, counter_ticks), duration_s=3, interval_s=1)

    dpc = cap.summary["sampling"]["dpc_time_percent"]
    assert dpc["max"] == 9.0
    assert dpc["mean"] == 4.0
    assert cap.summary["sampling"]["samples"] == 4


def test_processes_that_appear_mid_window_have_no_rate_until_the_next_sample(capture):
    ticks = [
        [proc(1, "a.exe", cpu_s=1.0)],
        [proc(1, "a.exe", cpu_s=1.2), proc(2, "nuevo.exe", cpu_s=50.0)],
    ]
    cap = capture(scenario(ticks), duration_s=1, interval_s=1)

    rows = {r["name"]: r for r in cap.csv("sampling/processes_all.csv")}
    assert rows["nuevo.exe"]["cpu_percent"] == ""
    assert float(rows["a.exe"]["cpu_percent"]) == 5.0


def test_no_window_when_duration_is_zero(capture):
    cap = capture(fixture_ports("sampling"), duration_s=0)

    assert "sampling" not in cap.manifest["domains"]
