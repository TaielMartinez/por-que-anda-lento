"""Historial: eventos de los últimos días que ayudan a ver si el Síntoma es un patrón."""

from conftest import fixture_ports

from lento.domains.history import SOURCES, source_query


def event(time, event_id=7, provider="disk", level=2, message="error"):
    return {"provider": provider, "event_id": event_id, "level": level, "time_created": time,
            "record_id": 1, "data": {}, "message": message}


def with_events(source_name, events):
    ports = fixture_ports("history")
    log, xpath = source_query(next(s for s in SOURCES if s.name == source_name), days=7)
    ports.set("events", log, xpath, 200, response=events)
    return ports


def test_one_file_per_source(capture):
    cap = capture(fixture_ports("history"))

    for source in SOURCES:
        data = cap.json(f"history/{source.name}.json")
        assert data["days"] == 7
        assert isinstance(data["events"], list)
    assert cap.domain("history")["status"] in ("complete", "partial")


def test_summary_counts_events_per_source_and_day(capture):
    cap = capture(with_events("disk", [
        event("2026-09-27T10:00:00-03:00"),
        event("2026-09-27T11:00:00-03:00"),
        event("2026-09-25T09:00:00-03:00"),
    ]))

    disk = cap.summary["history"]["disk"]
    assert disk["total"] == 3
    assert disk["by_day"] == {"2026-09-25": 1, "2026-09-27": 2}
    assert disk["truncated"] is False


def test_hitting_the_cap_marks_the_source_as_truncated(capture):
    cap = capture(with_events("whea", [event("2026-09-27T10:00:00-03:00", provider="WHEA")] * 200))

    assert cap.json("history/whea.json")["truncated"] is True
    assert cap.summary["history"]["whea"]["truncated"] is True
    assert "tope" in cap.entry("history/whea.json")["note"]


def test_an_unreadable_source_is_partial_and_the_rest_continue(capture):
    ports = fixture_ports("history")
    log, xpath = source_query(next(s for s in SOURCES if s.name == "diagnostics_performance"), days=7)
    ports.fail("events", log, xpath, 200, reason="acceso denegado")

    cap = capture(ports)

    entry = cap.entry("history/diagnostics_performance.json")
    assert entry["status"] == "partial"
    assert "acceso denegado" in entry["reason"]
    assert cap.exists("history/disk.json")
    assert cap.summary["history"]["diagnostics_performance"]["total"] is None
