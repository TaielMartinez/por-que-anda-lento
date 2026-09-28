"""Traza ETW durante la Ventana de muestreo: DPC/ISR por driver y red por proceso.

Las salidas de xperf siguen el formato documentado de `xperf -a dpcisr` y del volcado
(`dumper`). Reemplazarlas por grabaciones reales después de la Preparación.
"""

from conftest import fixture_ports

XPERF = "C:\\Program Files (x86)\\Windows Kits\\10\\Windows Performance Toolkit\\xperf.exe"

DPCISR = """\
--------------------------------------------------------------------------------
DPC Info
--------------------------------------------------------------------------------
Total = 1000 for module ntoskrnl.exe
Elapsed Time, >        0 usecs AND <=        1 usecs,    900, or  90.00%
Elapsed Time, >        1 usecs AND <=        2 usecs,    100, or  10.00%
Total = 50 for module nvlddmkm.sys
Elapsed Time, >        0 usecs AND <=        1 usecs,     10, or  20.00%
Elapsed Time, >      512 usecs AND <=     1024 usecs,     30, or  60.00%
Elapsed Time, >     2048 usecs AND <=     4096 usecs,     10, or  20.00%

--------------------------------------------------------------------------------
Interrupt (ISR) Info
--------------------------------------------------------------------------------
Total = 200 for module USBPORT.SYS
Elapsed Time, >        8 usecs AND <=       16 usecs,    200, or 100.00%
"""

DUMP = """\
BeginHeader
            TcpIp/Send,  TimeStamp,     Process Name ( PID),   ThreadID,  size,  daddr,  saddr
            TcpIp/Recv,  TimeStamp,     Process Name ( PID),   ThreadID,  size,  daddr,  saddr
            UdpIp/Send,  TimeStamp,     Process Name ( PID),   ThreadID,  size,  daddr,  saddr
     TcpIp/Retransmit,  TimeStamp,     Process Name ( PID),   ThreadID,  size,  daddr,  saddr
EndHeader
            TcpIp/Send,     500000,   steam.exe ( 4242),       100,   1000,  1.1.1.1,  2.2.2.2
            TcpIp/Recv,     700000,   steam.exe ( 4242),       100,   9000,  1.1.1.1,  2.2.2.2
            UdpIp/Send,     900000, discord.exe ( 5000),       200,    500,  3.3.3.3,  2.2.2.2
            TcpIp/Recv,    1500000,   steam.exe ( 4242),       100,  20000,  1.1.1.1,  2.2.2.2
     TcpIp/Retransmit,    1600000,   steam.exe ( 4242),       100,  99999,  1.1.1.1,  2.2.2.2
"""


def with_wpt(dpcisr=DPCISR, dump=DUMP, keep=False, etl=None):
    ports = fixture_ports("sampling")
    ports.set("tool_path", "wpt", response=XPERF)
    ports.set("etw_start", XPERF, response={"started": True})
    ports.set("etw_stop", XPERF, keep, response={"dpcisr": dpcisr, "network_dump": dump, "etl": etl})
    return ports


def test_dpc_and_isr_are_summarised_per_driver(capture):
    cap = capture(with_wpt(), duration_s=2, interval_s=1, only=["sampling"])

    rows = {(r["kind"], r["module"]): r for r in cap.csv("sampling/dpc_isr_by_driver.csv")}
    nv = rows[("dpc", "nvlddmkm.sys")]
    assert nv["count"] == "50"
    assert nv["count_over_1ms"] == "10"
    assert nv["max_usecs_bucket"] == "4096"
    assert rows[("isr", "USBPORT.SYS")]["count"] == "200"
    top = cap.summary["sampling"]["dpc_isr_top_drivers"][0]
    assert top["module"] == "nvlddmkm.sys" and top["kind"] == "dpc"


def test_network_traffic_is_attributed_to_processes_per_sample(capture):
    cap = capture(with_wpt(), duration_s=2, interval_s=1, only=["sampling"])

    rows = cap.csv("sampling/processes_top_net.csv")
    first = [r for r in rows if r["t_s"] == "1.0"]
    assert [(r["name"], r["sent_bytes_per_s"], r["recv_bytes_per_s"]) for r in first] == [
        ("steam.exe", "1000.0", "9000.0"),
        ("discord.exe", "500.0", "0.0"),
    ]
    second = [r for r in rows if r["t_s"] == "2.0"]
    assert [(r["name"], r["recv_bytes_per_s"]) for r in second] == [("steam.exe", "20000.0")]
    assert first[0]["rank"] == "1"
    assert cap.summary["sampling"]["top_net_processes"][0]["name"] == "steam.exe"


def test_etl_is_deleted_unless_asked_and_the_manifest_says_so(capture):
    cap = capture(with_wpt(), duration_s=1, interval_s=1, only=["sampling"])
    assert cap.manifest["etw"] == {"trace": True, "etl_kept": False, "etl_path": None}

    kept = with_wpt(keep=True, etl="C:\\captura\\raw\\trace.etl")
    cap = capture(kept, duration_s=1, interval_s=1, keep_etl=True, only=["sampling"])
    assert cap.manifest["etw"] == {"trace": True, "etl_kept": True, "etl_path": "C:\\captura\\raw\\trace.etl"}


def test_without_wpt_the_etw_files_fail_and_the_window_continues(capture):
    ports = fixture_ports("sampling")
    ports.set("tool_path", "wpt", response=None)

    cap = capture(ports, duration_s=1, interval_s=1, only=["sampling"])

    for name in ("dpc_isr_by_driver", "processes_top_net"):
        entry = cap.entry(f"sampling/{name}.csv")
        assert entry["status"] == "failed"
        assert "WPT" in entry["reason"]
    assert cap.entry("sampling/dpc_interrupt.csv")["status"] == "complete"
    assert cap.manifest["etw"]["trace"] is False


def test_a_trace_that_cannot_start_is_reported(capture):
    ports = with_wpt()
    ports.fail("etw_start", XPERF, reason="xperf: ya hay una sesión del kernel activa")

    cap = capture(ports, duration_s=1, interval_s=1, only=["sampling"])

    assert "sesión del kernel" in cap.entry("sampling/dpc_isr_by_driver.csv")["reason"]
