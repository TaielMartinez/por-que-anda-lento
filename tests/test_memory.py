"""Dominio memory: ¿a dónde se va la RAM?"""

from conftest import fixture_ports

from lento.domains.memory import COUNTERS

BASE = "snapshot/memory"
GiB = 1024**3
MiB = 1024**2


def scenario(**overrides):
    """Contadores de una PC de 24 GiB con valores redondos (ejemplo resuelto a mano)."""
    values = {
        "\\Memory\\Available Bytes": 5 * GiB,
        "\\Memory\\Committed Bytes": 20 * GiB,
        "\\Memory\\Commit Limit": 40 * GiB,
        "\\Memory\\Cache Bytes": 1 * GiB,
        "\\Memory\\Pool Nonpaged Bytes": 1 * GiB,
        "\\Memory\\Pool Paged Bytes": 2 * GiB,
        "\\Memory\\Pool Paged Resident Bytes": 1 * GiB,
        "\\Memory\\System Cache Resident Bytes": 512 * MiB,
        "\\Memory\\System Code Resident Bytes": 0,
        "\\Memory\\System Driver Resident Bytes": 256 * MiB,
        "\\Memory\\Standby Cache Core Bytes": 1 * GiB,
        "\\Memory\\Standby Cache Normal Priority Bytes": 2 * GiB,
        "\\Memory\\Standby Cache Reserve Bytes": 1 * GiB,
        "\\Memory\\Modified Page List Bytes": 256 * MiB,
        "\\Memory\\Free & Zero Page List Bytes": 1 * GiB,
        "\\Process(_Total)\\Working Set - Private": 11 * GiB,
        "\\Process(Memory Compression)\\Working Set": 1 * GiB,
    }
    values.update(overrides)
    ports = fixture_ports("memory")
    ports.set("counters", COUNTERS, response=values)
    info = ports.performance_info()
    info["physical_total_bytes"] = 24 * GiB
    ports.set("performance_info", response=info)
    return ports


def test_attribution_splits_used_ram_between_processes_and_the_rest(capture):
    cap = capture(scenario())

    a = cap.json(f"{BASE}/attribution.json")
    # 24 - 5 disponibles = 19 GiB usados; 11 privados totales - 1 de compresión = 10 en procesos.
    assert a["used_bytes"] == 19 * GiB
    assert a["processes_private_working_set_bytes"] == 10 * GiB
    assert a["unattributed_to_processes_bytes"] == 9 * GiB
    assert a["breakdown"] == {
        "nonpaged_pool_bytes": 1 * GiB,
        "paged_pool_resident_bytes": 1 * GiB,
        "system_cache_resident_bytes": 512 * MiB,
        "system_driver_resident_bytes": 256 * MiB,
        "system_code_resident_bytes": 0,
        "compression_store_bytes": 1 * GiB,
        "modified_page_list_bytes": 256 * MiB,
        # 9 GiB - 4 GiB explicados = 5 GiB (memoria compartida, tablas de páginas, memoria bloqueada por drivers...)
        "unexplained_bytes": 5 * GiB,
    }


def test_inflated_nonpaged_pool_shows_up_in_the_summary(capture):
    ports = scenario(**{"\\Memory\\Pool Nonpaged Bytes": 6 * GiB})
    tags = ports.pool_tags()
    tags.append({"tag": "Leak", "paged_allocs": 0, "paged_frees": 0, "paged_bytes": 0,
                 "nonpaged_allocs": 900000, "nonpaged_frees": 10, "nonpaged_bytes": 5 * GiB})
    ports.set("pool_tags", response=tags)

    cap = capture(ports)

    s = cap.summary["memory"]
    assert s["unattributed_breakdown"]["nonpaged_pool_bytes"] == 6 * GiB
    assert s["top_nonpaged_pool_tags"][0] == {"tag": "Leak", "nonpaged_bytes": 5 * GiB}
    pool = cap.json(f"{BASE}/pool_tags.json")
    assert pool[0]["tag"] == "Leak"
    assert pool[0]["nonpaged_outstanding_allocs"] == 900000 - 10


def test_page_lists_and_compression(capture):
    cap = capture(scenario())

    lists = cap.json(f"{BASE}/page_lists.json")
    assert lists["standby_bytes"] == 4 * GiB
    assert lists["standby"]["normal_priority_bytes"] == 2 * GiB
    assert lists["modified_bytes"] == 256 * MiB
    assert lists["free_and_zero_bytes"] == 1 * GiB
    assert cap.json(f"{BASE}/compression.json")["compression_store_bytes"] == 1 * GiB


def test_real_capture_is_consistent(capture):
    cap = capture(fixture_ports("memory"))

    totals = cap.json(f"{BASE}/totals.json")
    assert totals["physical_used_bytes"] == totals["physical_total_bytes"] - totals["physical_available_bytes"]
    assert 0 < cap.summary["memory"]["used_percent"] < 100
    assert cap.json(f"{BASE}/pool_tags.json"), "debe haber tags de pool"
    for name in ("totals", "page_lists", "compression", "pool_tags", "attribution"):
        assert cap.entry(f"{BASE}/{name}.json")["status"] == "complete", name


def test_pool_tags_unavailable_leaves_the_file_partial(capture):
    ports = scenario()
    ports.fail("pool_tags", reason="acceso denegado")

    cap = capture(ports)

    assert cap.json(f"{BASE}/pool_tags.json") == []
    assert "acceso denegado" in cap.entry(f"{BASE}/pool_tags.json")["reason"]
    assert cap.json(f"{BASE}/attribution.json")["used_bytes"] == 19 * GiB


def test_missing_counters_are_null_and_partial(capture):
    cap = capture(scenario(**{"\\Memory\\Standby Cache Core Bytes": None}))

    lists = cap.json(f"{BASE}/page_lists.json")
    assert lists["standby"]["core_bytes"] is None
    assert cap.entry(f"{BASE}/page_lists.json")["status"] == "partial"


def test_summary_percentages(capture):
    s = capture(scenario()).summary["memory"]
    assert s["used_percent"] == round(19 / 24 * 100, 1)
    assert s["commit_percent"] == 50.0
