"""Dominio processes: qué corre y para qué se usa la PC."""

from conftest import fixture_ports

BASE = "snapshot/processes"


def test_process_list_has_memory_cpu_and_threads_per_process(capture):
    cap = capture(fixture_ports("processes"))

    rows = cap.json(f"{BASE}/list.json")
    by_name = {r["name"]: r for r in rows}
    assert "explorer.exe" in by_name
    explorer = by_name["explorer.exe"]
    for field in ("pid", "ppid", "private_bytes", "working_set_bytes", "cpu_s", "num_threads", "num_handles"):
        assert field in explorer
    assert explorer["private_bytes"] > 0
    assert rows == sorted(rows, key=lambda r: r["private_bytes"] or 0, reverse=True)


def test_command_lines_are_kept_without_masking(capture):
    ports = fixture_ports("processes")
    rows = ports.processes()
    rows[0]["cmdline"] = ["tool.exe", "--token", "abc123SECRET", "password=hunter2"]
    ports.set("processes", response=rows)

    cap = capture(ports)

    cmdlines = {r["pid"]: r["cmdline"] for r in cap.json(f"{BASE}/cmdlines.json")}
    assert cmdlines[rows[0]["pid"]] == "tool.exe --token abc123SECRET password=hunter2"


def test_tree_nests_children_under_their_parent(capture):
    ports = fixture_ports("processes")
    ports.set("processes", response=[
        _proc(4, 0, "System"),
        _proc(100, 4, "smss.exe"),
        _proc(200, 100, "csrss.exe"),
        _proc(300, 999, "huerfano.exe"),
    ])

    cap = capture(ports)

    tree = cap.json(f"{BASE}/tree.json")
    assert [n["name"] for n in tree] == ["System", "huerfano.exe"]
    assert tree[0]["children"][0]["name"] == "smss.exe"
    assert tree[0]["children"][0]["children"][0]["pid"] == 200


def test_io_and_handles_are_separate_files(capture):
    cap = capture(fixture_ports("processes"))

    io = cap.json(f"{BASE}/io.json")
    assert {"pid", "name", "io_read_bytes", "io_write_bytes"} <= set(io[0])
    assert io == sorted(io, key=lambda r: (r["io_read_bytes"] or 0) + (r["io_write_bytes"] or 0), reverse=True)
    handles = cap.json(f"{BASE}/handles.json")
    assert handles == sorted(handles, key=lambda r: r["num_handles"] or 0, reverse=True)


def test_inaccessible_processes_make_files_partial_with_a_reason(capture):
    ports = fixture_ports("processes")
    ports.set("processes", response=[_proc(4, 0, "System", private_bytes=None), _proc(8, 4, "a.exe")])

    cap = capture(ports)

    entry = cap.entry(f"{BASE}/list.json")
    assert entry["status"] == "partial"
    assert "1 proceso" in entry["reason"]
    assert cap.domain("processes")["status"] == "partial"


def test_summary_totals(capture):
    ports = fixture_ports("processes")
    ports.set("processes", response=[
        _proc(4, 0, "System", private_bytes=100, working_set_bytes=1000),
        _proc(8, 4, "a.exe", private_bytes=50, working_set_bytes=500),
    ])

    cap = capture(ports)

    assert cap.summary["processes"] == {
        "count": 2,
        "private_bytes_total": 150,
        "working_set_bytes_total": 1500,
        "threads_total": 2,
        "handles_total": 20,
        "inaccessible_count": 0,
    }


def _proc(pid, ppid, name, private_bytes=10, working_set_bytes=20):
    return {
        "pid": pid, "ppid": ppid, "name": name, "exe": None, "cmdline": [name], "username": None,
        "create_time": 1.0, "status": "running", "num_threads": 1, "num_handles": 10,
        "cpu_user_s": 1.0, "cpu_system_s": 0.5, "working_set_bytes": working_set_bytes,
        "peak_working_set_bytes": working_set_bytes, "private_bytes": private_bytes,
        "paged_pool_bytes": 1, "nonpaged_pool_bytes": 1, "io_read_bytes": 1, "io_write_bytes": 1,
        "io_read_count": 1, "io_write_count": 1, "io_other_bytes": 1, "priority": 32,
    }
