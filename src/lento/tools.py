"""Herramientas externas instaladas por la Preparación."""

from __future__ import annotations

from pathlib import Path


def installed_path(name: str, tools_dir: Path) -> Path | None:
    candidate = tools_dir / name
    return candidate if candidate.exists() else None
