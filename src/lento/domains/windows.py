"""Dominio windows: ventana en primer plano y ventanas visibles (qué está haciendo el usuario)."""

from __future__ import annotations

from lento.capture import DomainWriter
from lento.ports import Ports

NAME = "windows"
BASE = "snapshot/windows"
DOC = "windows"


def collect(ports: Ports, out: DomainWriter) -> None:
    rows = ports.windows()
    foreground = next((w for w in rows if w.get("foreground")), None)
    out.json("foreground", foreground, "¿Qué ventana tenía el foco en el momento de la Captura?")
    out.json("visible", rows, "¿Qué ventanas estaban abiertas y visibles, de qué proceso y con qué título?")
    out.summary().update(
        foreground_process=foreground.get("process_name") if foreground else None,
        foreground_title=foreground.get("title") if foreground else None,
        visible_count=len(rows),
    )
