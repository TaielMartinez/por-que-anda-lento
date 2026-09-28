"""Dominios services, startup, scheduled_tasks, drivers, security y updates."""

from conftest import fixture_ports

from lento.domains import drivers, scheduled_tasks, security, startup, updates

AUTORUNSC = "C:\\tools\\sysinternals\\autorunsc64.exe"
SIGCHECK = "C:\\tools\\sysinternals\\sigcheck64.exe"

# Formato CSV de `autorunsc -c` (encabezado de Autoruns 14.x).
AUTORUNS_CSV = (
    "Time,Entry Location,Entry,Enabled,Category,Profile,Description,Signer,Company,Image Path,Version,Launch String\n"
    "20260920 10:00,HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run,RGBFusion,enabled,Logon,Taiel,"
    "RGB Fusion,(Not Verified) GIGA-BYTE,GIGA-BYTE,c:\\program files\\rgb\\rgb.exe,2.0,\"\"\"c:\\program files\\rgb\\rgb.exe\"\" -tray\"\n"
    "20260101 09:00,HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run,SecurityHealth,enabled,Logon,System-wide,"
    "Windows Security,(Verified) Microsoft Windows,Microsoft Corporation,c:\\windows\\system32\\securityhealthsystray.exe,"
    "10.0,%windir%\\system32\\SecurityHealthSystray.exe\n"
    "20250101 09:00,HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run,Viejo,disabled,Logon,System-wide,"
    "Viejo,(Verified) X,X,c:\\x.exe,1.0,c:\\x.exe\n"
)

# Formato CSV de `sigcheck -c -u` (solo archivos sin firma válida).
SIGCHECK_CSV = (
    "Path,Verified,Date,Publisher,Company,Description,Product,Product Version,File Version,Machine Type\n"
    "c:\\windows\\system32\\drivers\\raro.sys,Unsigned,10:00 01/02/2015,n/a,Raro Inc,Raro driver,Raro,1.0,1.0,64-bit\n"
)


def with_tools():
    ports = fixture_ports("running")
    ports.set("tool_path", "autorunsc", response=AUTORUNSC)
    ports.set("tool_path", "sigcheck", response=SIGCHECK)
    ports.set("run", [AUTORUNSC, *startup.AUTORUNS_ARGS], 300, response={"returncode": 0, "stdout": AUTORUNS_CSV, "stderr": ""})
    ports.set("run", [SIGCHECK, *drivers.SIGCHECK_ARGS], 300, response={"returncode": 0, "stdout": SIGCHECK_CSV, "stderr": ""})
    return ports


def test_services_list_state_and_start_mode(capture):
    cap = capture(fixture_ports("running"))

    services = cap.json("snapshot/services/list.json")
    assert any(s["name"] == "wuauserv" for s in services)
    running = cap.json("snapshot/services/running.json")
    assert running and all(s["state"] == "Running" for s in running)
    assert cap.summary["services"]["running_count"] == len(running)


def test_startup_entries_from_autoruns(capture):
    cap = capture(with_tools())

    entries = cap.json("snapshot/startup/entries.json")
    assert [e["entry"] for e in entries] == ["RGBFusion", "SecurityHealth", "Viejo"]
    rgb = entries[0]
    assert rgb["enabled"] is True
    assert rgb["signer"] == "(Not Verified) GIGA-BYTE"
    assert rgb["launch_string"] == "\"c:\\program files\\rgb\\rgb.exe\" -tray"
    assert cap.summary["startup"]["enabled_count"] == 2
    assert cap.summary["startup"]["not_verified"] == ["RGBFusion"]
    assert cap.entry("snapshot/startup/entries.json")["status"] == "complete"


def test_startup_without_autoruns_falls_back_to_run_keys_and_is_partial(capture):
    ports = fixture_ports("running")
    ports.set("tool_path", "autorunsc", response=None)

    cap = capture(ports)

    entry = cap.entry("snapshot/startup/entries.json")
    assert entry["status"] == "partial"
    assert "autorunsc" in entry["reason"]
    assert all(e["source"] == "registry" for e in cap.json("snapshot/startup/entries.json"))


def test_unsigned_drivers_from_sigcheck(capture):
    cap = capture(with_tools())

    unsigned = cap.json("snapshot/drivers/unsigned.json")
    assert unsigned == [{
        "path": "c:\\windows\\system32\\drivers\\raro.sys", "verified": "Unsigned", "company": "Raro Inc",
        "description": "Raro driver", "file_version": "1.0", "date": "10:00 01/02/2015",
    }]
    assert cap.summary["drivers"]["unsigned"] == ["c:\\windows\\system32\\drivers\\raro.sys"]


def test_drivers_without_sigcheck_use_windows_signature_info(capture):
    ports = fixture_ports("running")
    ports.set("tool_path", "sigcheck", response=None)
    ports.set("wmi", drivers.SIGNED_DRIVERS_QUERY, "root\\cimv2", response=[
        {"DeviceName": "Placa rara", "DriverVersion": "1.0", "DriverDate": "20150101000000.000000-000",
         "DriverProviderName": "Raro", "IsSigned": False, "InfName": "oem9.inf"},
        {"DeviceName": "NVIDIA GeForce RTX 3090", "DriverVersion": "32.0.15.9186",
         "DriverDate": "20260120000000.000000-000", "DriverProviderName": "NVIDIA", "IsSigned": True, "InfName": "oem1.inf"},
    ])

    cap = capture(ports)

    assert cap.entry("snapshot/drivers/unsigned.json")["status"] == "partial"
    assert [d["device"] for d in cap.json("snapshot/drivers/unsigned.json")] == ["Placa rara"]
    oldest = cap.summary["drivers"]["oldest_third_party"]
    assert oldest[0] == {"device": "Placa rara", "provider": "Raro", "date": "2015-01-01", "version": "1.0"}


def test_scheduled_tasks_separate_third_party(capture):
    ports = fixture_ports("running")
    ports.set("run", scheduled_tasks.COMMAND, 300, response={"returncode": 0, "stderr": "", "stdout": (
        '[{"path":"\\\\Microsoft\\\\Windows\\\\Defrag\\\\","name":"ScheduledDefrag","state":"Ready","author":"Microsoft",'
        '"actions":["defrag.exe -c"],"triggers":["MSFT_TaskDailyTrigger"],"last_run":"2026-09-28T11:30:00-03:00",'
        '"next_run":null,"last_result":0},'
        '{"path":"\\\\","name":"Updater RGB","state":"Running","author":"GIGABYTE",'
        '"actions":["C:\\\\rgb\\\\up.exe"],"triggers":["MSFT_TaskLogonTrigger"],"last_run":"2026-09-28T12:00:00-03:00",'
        '"next_run":null,"last_result":0}]'
    )})

    cap = capture(ports)

    assert [t["name"] for t in cap.json("snapshot/scheduled_tasks/third_party.json")] == ["Updater RGB"]
    assert len(cap.json("snapshot/scheduled_tasks/enabled.json")) == 2
    s = cap.summary["scheduled_tasks"]
    assert s["running"] == ["\\Updater RGB"]
    assert s["ran_last_hour"] == ["\\Microsoft\\Windows\\Defrag\\ScheduledDefrag", "\\Updater RGB"]


def test_defender_scan_in_progress_is_detected(capture):
    ports = fixture_ports("running")
    ports.set("wmi", security.DEFENDER_STATUS_QUERY, security.DEFENDER_NS, response=[{
        "AMRunningMode": "Normal", "AntivirusEnabled": True, "RealTimeProtectionEnabled": True,
        "QuickScanStartTime": "20260928115000.000000-180", "QuickScanEndTime": "20260927100000.000000-180",
        "FullScanStartTime": None, "FullScanEndTime": None, "AntivirusSignatureAge": 1,
    }])

    cap = capture(ports)

    status = cap.json("snapshot/security/defender_status.json")
    assert status["scan_in_progress"] == "quick"
    assert cap.summary["security"]["defender_scan_in_progress"] == "quick"


def test_update_activity_and_pending_reboot(capture):
    ports = fixture_ports("running")
    ports.set("wmi", updates.SERVICES_QUERY, "root\\cimv2", response=[
        {"Name": "wuauserv", "State": "Running"}, {"Name": "TrustedInstaller", "State": "Running"},
        {"Name": "UsoSvc", "State": "Running"},
    ])
    ports.set("registry_values", updates.REBOOT_REQUIRED_KEY, response={})

    cap = capture(ports)

    activity = cap.json("snapshot/updates/activity.json")
    assert activity["installing"] is True
    assert activity["pending_reboot"] is True
    assert cap.summary["updates"]["installing"] is True
    assert cap.json("snapshot/updates/installed.json") is not None
