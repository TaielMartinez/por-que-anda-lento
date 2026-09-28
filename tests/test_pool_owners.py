"""Tags del pool del kernel traducidos al driver dueño."""

from conftest import fixture_ports

from lento.domains.memory import driver_search_command

MiB = 1024**2
POOLTAG = "C:\\Kits\\Debuggers\\x64\\triage\\pooltag.txt"

# Formato de pooltag.txt de Debugging Tools for Windows.
POOLTAG_TXT = """\
rem
rem Pooltag.txt
rem
NVRM - nvlddmkm.sys - NVIDIA Resource Manager
Mm   - nt!mm        - general Mm Allocations
EtwB - nt!etw       - Etw Buffer
"""


def tag(name, nonpaged=0, paged=0):
    return {"tag": name, "paged_allocs": 10, "paged_frees": 1, "paged_bytes": paged,
            "nonpaged_allocs": 10, "nonpaged_frees": 1, "nonpaged_bytes": nonpaged}


def scenario(with_pooltag=True):
    ports = fixture_ports("memory")
    ports.set("pool_tags", response=[
        tag("Leak", nonpaged=5000 * MiB), tag("NVRM", nonpaged=60 * MiB), tag("Mm  ", paged=40 * MiB),
        tag("EtwB", nonpaged=30 * MiB),
    ])
    ports.set("tool_path", "pooltag", response=POOLTAG if with_pooltag else None)
    ports.set("file_text", POOLTAG, response=POOLTAG_TXT)
    ports.set("run", driver_search_command("Leak"), 120, response={
        "returncode": 0, "stderr": "", "stdout": "C:\\Windows\\System32\\drivers\\rgbfusion.sys\r\n",
    })
    for unknown in ("NVRM", "Mm  ", "EtwB"):
        ports.set("run", driver_search_command(unknown), 120, response={"returncode": 1, "stdout": "", "stderr": ""})
    return ports


def test_tags_are_mapped_with_pooltag_and_driver_search(capture):
    cap = capture(scenario(), only=["memory"])

    owners = {o["tag"]: o for o in cap.json("snapshot/memory/pool_tag_owners.json")}
    assert owners["NVRM"]["drivers"] == ["nvlddmkm.sys"]
    assert owners["NVRM"]["source"] == "pooltag.txt"
    assert owners["NVRM"]["description"] == "NVIDIA Resource Manager"
    assert owners["Mm  "]["drivers"] == ["nt!mm"]
    assert owners["Leak"] == {
        "tag": "Leak", "nonpaged_bytes": 5000 * MiB, "paged_bytes": 0,
        "drivers": ["rgbfusion.sys"], "description": None, "source": "driver_search",
    }


def test_summary_points_at_the_driver_holding_most_pool(capture):
    cap = capture(scenario(), only=["memory"])

    s = cap.summary["memory"]
    assert s["top_drivers_by_nonpaged_pool"][0] == {"driver": "rgbfusion.sys", "nonpaged_bytes": 5000 * MiB}
    assert s["top_drivers_by_paged_pool"][0] == {"driver": "nt!mm", "paged_bytes": 40 * MiB}


def test_unmapped_tags_are_reported_as_unknown(capture):
    ports = scenario()
    ports.set("run", driver_search_command("Leak"), 120, response={"returncode": 1, "stdout": "", "stderr": ""})

    cap = capture(ports, only=["memory"])

    owners = {o["tag"]: o for o in cap.json("snapshot/memory/pool_tag_owners.json")}
    assert owners["Leak"]["source"] == "unknown"
    assert owners["Leak"]["drivers"] == []


def test_without_pooltag_txt_only_driver_search_is_used_and_it_is_partial(capture):
    cap = capture(scenario(with_pooltag=False), only=["memory"])

    owners = {o["tag"]: o for o in cap.json("snapshot/memory/pool_tag_owners.json")}
    assert owners["Leak"]["drivers"] == ["rgbfusion.sys"]
    assert owners["NVRM"]["source"] == "unknown"
    entry = cap.entry("snapshot/memory/pool_tag_owners.json")
    assert entry["status"] == "partial"
    assert "pooltag" in entry["reason"]
