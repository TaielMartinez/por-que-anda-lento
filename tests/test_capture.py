"""Estructura de la Captura: carpeta, manifest y Resumen."""

from pathlib import Path

from conftest import fixture_ports


def test_capture_folder_is_named_after_start_time(capture):
    cap = capture(fixture_ports("system"))

    assert cap.path.name == "2026-09-28_120405"
    assert cap.manifest["started_at"] == "2026-09-28T12:04:05-03:00"


def test_manifest_lists_every_file_with_question_size_and_status(capture):
    cap = capture(fixture_ports("system"))

    manifest = cap.manifest
    assert manifest["schema_version"] == 1
    assert manifest["files"], "el manifest debe listar archivos"
    for entry in manifest["files"]:
        file = cap.path / entry["path"]
        assert file.exists(), entry["path"]
        assert entry["bytes"] == file.stat().st_size
        assert entry["question"].endswith("?"), entry["path"]
        assert entry["status"] in ("complete", "partial", "failed")


def test_summary_is_written_next_to_manifest(capture):
    cap = capture(fixture_ports("system"))

    assert Path(cap.path / "summary.json").exists()
    assert "system" in cap.summary


def test_a_domain_that_crashes_is_marked_failed_and_the_capture_continues(capture, monkeypatch):
    import lento.domains.system as system

    def boom(ports, out):
        raise RuntimeError("explotó")

    monkeypatch.setattr(system, "collect", boom)
    cap = capture(fixture_ports("system"))

    assert cap.domain("system")["status"] == "failed"
    assert "explotó" in cap.domain("system")["reasons"][0]
    assert cap.exists("manifest.json")


def test_reference_flag_is_recorded_in_manifest(capture):
    assert capture(fixture_ports("system"), reference=True).manifest["is_reference"] is True
