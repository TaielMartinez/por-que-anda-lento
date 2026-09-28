"""Escritura de una Captura: archivos de una sola pregunta, manifest y Resumen."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1

COMPLETE = "complete"
PARTIAL = "partial"
FAILED = "failed"


@dataclass
class FileEntry:
    path: str
    domain: str
    question: str
    bytes: int
    status: str
    reason: str | None


@dataclass
class DomainResult:
    status: str = COMPLETE
    reasons: list[str] = field(default_factory=list)


class CaptureWriter:
    """Acumula archivos, estados por dominio y el Resumen de una Captura."""

    def __init__(self, root: Path):
        self.root = root
        self.files: list[FileEntry] = []
        self.domains: dict[str, DomainResult] = {}
        self.summary: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}

    def domain(self, name: str, base: str) -> DomainWriter:
        self.domains.setdefault(name, DomainResult())
        return DomainWriter(self, name, base)

    def fail_domain(self, name: str, reason: str) -> None:
        result = self.domains.setdefault(name, DomainResult())
        result.status = FAILED
        result.reasons.append(reason)

    def write_manifest(self) -> None:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            **self.metadata,
            "domains": {
                name: {"status": r.status, "reasons": r.reasons}
                for name, r in self.domains.items()
            },
            "files": [vars(f) for f in self.files],
        }
        self._write_text("summary.json", _dumps(self.summary))
        self._write_text("manifest.json", _dumps(manifest))

    def _write_text(self, rel: str, text: str) -> int:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode("utf-8")
        path.write_bytes(data)
        return len(data)


class DomainWriter:
    """Escribe los archivos de un dominio bajo su carpeta y registra cada uno en el manifest."""

    def __init__(self, capture: CaptureWriter, name: str, base: str):
        self.capture = capture
        self.name = name
        self.base = base

    @property
    def result(self) -> DomainResult:
        return self.capture.domains[self.name]

    def partial(self, reason: str) -> None:
        if self.result.status == COMPLETE:
            self.result.status = PARTIAL
        self.result.reasons.append(reason)

    def summary(self, section: str | None = None) -> dict[str, Any]:
        """Sección del Resumen donde este dominio deja sus métricas derivadas."""
        return self.capture.summary.setdefault(section or self.name, {})

    def json(self, name: str, data: Any, question: str, reason: str | None = None) -> None:
        self._register(f"{name}.json", _dumps(data), question, reason)

    def csv(
        self,
        name: str,
        rows: Iterable[dict[str, Any]],
        question: str,
        columns: list[str],
        reason: str | None = None,
    ) -> None:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        self._register(f"{name}.csv", buf.getvalue(), question, reason)

    def text(self, name: str, text: str, question: str, reason: str | None = None) -> None:
        self._register(name, text, question, reason)

    def _register(self, filename: str, text: str, question: str, reason: str | None) -> None:
        rel = f"{self.base}/{filename}" if self.base else filename
        size = self.capture._write_text(rel, text)
        status = PARTIAL if reason else COMPLETE
        if reason:
            self.partial(f"{filename}: {reason}")
        self.capture.files.append(FileEntry(rel, self.name, question, size, status, reason))


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
