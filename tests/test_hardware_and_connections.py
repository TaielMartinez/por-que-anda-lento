"""Dominios storage, devices, network, windows y software."""

from conftest import fixture_ports

from lento.domains import devices, software, storage

GiB = 1024**3


def test_volumes_report_free_space(capture):
    ports = fixture_ports("hardware")
    ports.set("disks", response=[
        {"mountpoint": "C:\\", "device": "C:\\", "fstype": "NTFS", "opts": "rw,fixed",
         "total_bytes": 500 * GiB, "used_bytes": 480 * GiB, "free_bytes": 20 * GiB},
        {"mountpoint": "D:\\", "device": "D:\\", "fstype": "NTFS", "opts": "rw,fixed",
         "total_bytes": 1000 * GiB, "used_bytes": 100 * GiB, "free_bytes": 900 * GiB},
    ])

    cap = capture(ports)

    volumes = {v["mountpoint"]: v for v in cap.json("snapshot/storage/volumes.json")}
    assert volumes["C:\\"]["free_percent"] == 4.0
    assert cap.summary["storage"]["lowest_free_percent"] == {"mountpoint": "C:\\", "free_percent": 4.0}


def test_physical_disks_come_from_the_real_machine(capture):
    cap = capture(fixture_ports("hardware"))

    disks = cap.json("snapshot/storage/physical_disks.json")
    assert disks and all("health_status" in d for d in disks)


def test_smart_unavailable_leaves_the_file_partial(capture):
    ports = fixture_ports("hardware")
    ports.fail("wmi", storage.RELIABILITY_QUERY, storage.STORAGE_NS, reason="acceso denegado")

    cap = capture(ports)

    assert cap.json("snapshot/storage/smart.json") == []
    assert cap.entry("snapshot/storage/smart.json")["status"] == "partial"
    assert cap.domain("storage")["status"] == "partial"


def test_devices_with_errors_are_listed_separately(capture):
    ports = fixture_ports("hardware")
    ports.set("wmi", devices.PNP_QUERY, "root\\cimv2", response=[
        {"Name": "Mouse USB", "PNPClass": "Mouse", "Manufacturer": "Logi", "Status": "OK",
         "ConfigManagerErrorCode": 0, "PNPDeviceID": "USB\\VID_046D&PID_C52B\\1", "Present": True},
        {"Name": "Controlador roto", "PNPClass": "System", "Manufacturer": "X", "Status": "Error",
         "ConfigManagerErrorCode": 10, "PNPDeviceID": "PCI\\VEN_1\\2", "Present": True},
    ])

    cap = capture(ports)

    problems = cap.json("snapshot/devices/problems.json")
    assert [d["name"] for d in problems] == ["Controlador roto"]
    assert problems[0]["error_code"] == 10
    assert "no puede iniciar" in problems[0]["error_meaning"]
    assert [d["name"] for d in cap.json("snapshot/devices/usb.json")] == ["Mouse USB"]
    assert cap.summary["devices"]["problem_devices"] == ["Controlador roto"]


def test_network_connections_carry_process_names(capture):
    cap = capture(fixture_ports("hardware"))

    conns = cap.json("snapshot/network/connections.json")
    assert conns and "process_name" in conns[0]
    assert cap.json("snapshot/network/adapters.json")
    assert "connections_by_status" in cap.summary["network"]


def test_foreground_window_is_identified_with_its_title_unmasked(capture):
    ports = fixture_ports("hardware")
    ports.set("windows", response=[
        {"pid": 1, "process_name": "chrome.exe", "title": "Banco - mi cuenta", "foreground": False, "minimized": False},
        {"pid": 2, "process_name": "code.exe", "title": "secreto.txt - VS Code", "foreground": True, "minimized": False},
    ])

    cap = capture(ports)

    assert cap.json("snapshot/windows/foreground.json")["title"] == "secreto.txt - VS Code"
    visible = cap.json("snapshot/windows/visible.json")
    assert [w["title"] for w in visible] == ["Banco - mi cuenta", "secreto.txt - VS Code"]
    assert cap.summary["windows"]["foreground_process"] == "code.exe"


def test_software_lists_installed_programs_and_recent_installs(capture):
    ports = fixture_ports("hardware")
    for key in software.UNINSTALL_KEYS:
        ports.set("registry_subkey_values", key, response={})
    ports.set("registry_subkey_values", software.UNINSTALL_KEYS[0], response={
        "{A}": {"DisplayName": "Viejo", "DisplayVersion": "1.0", "Publisher": "P", "InstallDate": "20250101"},
        "{B}": {"DisplayName": "Nuevo driver", "DisplayVersion": "2.0", "Publisher": "Q", "InstallDate": "20260925",
                "EstimatedSize": 2048},
        "{C}": {"DisplayName": "Componente", "SystemComponent": 1},
        "{D}": {"Publisher": "sin nombre"},
    })

    cap = capture(ports)

    installed = cap.json("snapshot/software/installed.json")
    assert [s["name"] for s in installed] == ["Nuevo driver", "Viejo"]
    assert installed[0]["installed_on"] == "2026-09-25"
    assert installed[0]["size_bytes"] == 2048 * 1024
    assert cap.summary["software"]["installed_last_30_days"] == [
        {"name": "Nuevo driver", "version": "2.0", "installed_on": "2026-09-25"},
    ]
