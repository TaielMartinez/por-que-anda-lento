"""Prueba de humo: el Colector real en esta PC. Requiere admin; correr con `pytest -m smoke`."""

import json
import re
from pathlib import Path

import pytest

from lento.collector import DOMAINS, CollectOptions, collect

pytestmark = pytest.mark.smoke

DOCS = Path(__file__).parents[1] / "docs" / "capture"


def test_real_capture_matches_the_documented_schema(tmp_path):
    from lento.elevation import is_admin
    from lento.windows import WindowsPorts

    if not is_admin():
        pytest.skip("la prueba de humo necesita una terminal como administrador")

    root = collect(WindowsPorts(), tmp_path, CollectOptions(duration_s=10, interval_s=1))

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{6}(_\d+)?", root.name)
    assert isinstance(summary, dict)
    for module in DOMAINS:
        assert module.NAME in manifest["domains"], module.NAME
    for entry in manifest["files"]:
        path = root / entry["path"]
        assert path.exists(), entry["path"]
        assert path.stat().st_size == entry["bytes"]
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(manifest["domains"], ensure_ascii=False, indent=1))
