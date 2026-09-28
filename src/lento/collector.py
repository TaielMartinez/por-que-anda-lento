"""El Colector: observa el sistema a través de los puertos y produce una Captura."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from lento.capture import CaptureWriter
from lento.domains import processes, system
from lento.ports import Ports

# Cada dominio es un módulo con NAME, BASE (carpeta dentro de la Captura) y collect(ports, out).
DOMAINS: list[ModuleType] = [system, processes]


@dataclass
class CollectOptions:
    duration_s: float = 60
    interval_s: float = 1
    reference: bool = False
    keep_etl: bool = False
    only: list[str] | None = None  # restringe los dominios (grabación de fixtures)


def collect(ports: Ports, captures_dir: Path, options: CollectOptions) -> Path:
    started_at = ports.now()
    root = _new_capture_dir(Path(captures_dir), started_at)
    writer = CaptureWriter(root)
    writer.metadata.update(
        capture_id=root.name,
        started_at=started_at,
        finished_at=None,
        is_reference=options.reference,
        sampling={"duration_s": options.duration_s, "interval_s": options.interval_s},
    )

    for module in DOMAINS:
        if options.only is not None and module.NAME not in options.only:
            continue
        out = writer.domain(module.NAME, module.BASE)
        try:
            module.collect(ports, out)
        except Exception as e:  # noqa: BLE001 - un dominio roto no aborta la Captura
            writer.fail_domain(module.NAME, f"{type(e).__name__}: {e}")
            writer.metadata.setdefault("errors", {})[module.NAME] = traceback.format_exc()

    writer.metadata["finished_at"] = ports.now()
    writer.write_manifest()
    return root


def _new_capture_dir(captures_dir: Path, started_at: str) -> Path:
    base = f"{started_at[:10]}_{started_at[11:19].replace(':', '')}"
    candidate = captures_dir / base
    n = 1
    while candidate.exists():
        n += 1
        candidate = captures_dir / f"{base}_{n}"
    candidate.mkdir(parents=True)
    return candidate
