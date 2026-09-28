from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from lento.collector import CollectOptions, collect
from lento.ports import FixturePorts

FIXTURES = Path(__file__).parent / "fixtures"


@dataclass
class CaptureView:
    """Vista de solo lectura de una Captura generada, tal como la ve el agente."""

    path: Path

    @property
    def manifest(self) -> dict[str, Any]:
        return self.json("manifest.json")

    @property
    def summary(self) -> dict[str, Any]:
        return self.json("summary.json")

    def json(self, rel: str) -> Any:
        return json.loads((self.path / rel).read_text(encoding="utf-8"))

    def csv(self, rel: str) -> list[dict[str, str]]:
        with open(self.path / rel, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def entry(self, rel: str) -> dict[str, Any]:
        matches = [f for f in self.manifest["files"] if f["path"] == rel]
        assert matches, f"{rel} no está en el manifest"
        return matches[0]

    def domain(self, name: str) -> dict[str, Any]:
        return self.manifest["domains"][name]

    def exists(self, rel: str) -> bool:
        return (self.path / rel).exists()


def fixture_ports(*names: str) -> FixturePorts:
    return FixturePorts.load(*(FIXTURES / f"{n}.json" for n in names))


@pytest.fixture
def capture(tmp_path: Path):
    """Ejecuta el Colector completo contra puertos de fixture y devuelve la Captura."""

    def run(ports: FixturePorts, **options: Any) -> CaptureView:
        opts = CollectOptions(**{"duration_s": 0, **options})
        return CaptureView(collect(ports, tmp_path / "captures", opts))

    return run
