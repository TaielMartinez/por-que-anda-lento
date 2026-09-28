"""La documentación de la Captura cubre cada dominio y cada archivo que el Colector escribe."""

import re
from pathlib import Path

from conftest import FIXTURES, fixture_ports

from lento.collector import DOMAINS

DOCS = Path(__file__).parents[1] / "docs" / "capture"


def all_fixtures():
    return fixture_ports(*(p.stem for p in sorted(FIXTURES.glob("*.json"))))


def test_every_domain_has_a_document_linked_from_the_index():
    index = (DOCS / "README.md").read_text(encoding="utf-8")
    for module in DOMAINS:
        doc = DOCS / f"{module.DOC}.md"
        assert doc.exists(), f"falta {doc.name}"
        assert f"({doc.name})" in index, f"el índice no enlaza {doc.name}"


def test_every_written_file_is_documented_in_its_domain_document(capture):
    cap = capture(all_fixtures(), duration_s=3, interval_s=1)

    docs = {m.NAME: (DOCS / f"{m.DOC}.md").read_text(encoding="utf-8") for m in DOMAINS}
    for entry in cap.manifest["files"]:
        filename = entry["path"].rsplit("/", 1)[-1]
        stem = re.sub(r"\.(json|csv|txt)$", "", filename)
        assert stem in docs[entry["domain"]], f"{entry['path']} no está documentado"
