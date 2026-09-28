"""El Colector registra en el manifest qué herramientas de la Preparación faltan."""

from conftest import fixture_ports

from lento.tools import TOOLS


def ports_with_tools(installed: set[str]):
    ports = fixture_ports("system")
    for tool in TOOLS:
        ports.set("tool_path", tool.name, response=f"C:\\tools\\{tool.name}" if tool.name in installed else None)
    return ports


def test_missing_tools_are_listed_in_the_manifest(capture):
    cap = capture(ports_with_tools(installed={"librehardwaremonitor"}))

    missing = {t["name"]: t for t in cap.manifest["missing_tools"]}
    assert "librehardwaremonitor" not in missing
    assert "wpt" in missing
    assert missing["wpt"]["needed_for"]
    assert "uv run setup" in cap.manifest["missing_tools_hint"]


def test_no_missing_tools_when_everything_is_installed(capture):
    cap = capture(ports_with_tools(installed={t.name for t in TOOLS}))

    assert cap.manifest["missing_tools"] == []
    assert cap.manifest["missing_tools_hint"] is None
