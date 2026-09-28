"""Conversión del XML de un evento de Windows a un diccionario plano."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}


def parse_event_xml(xml: str) -> dict[str, Any]:
    root = ET.fromstring(xml)
    system = root.find("e:System", NS)
    assert system is not None

    def text(tag: str) -> str | None:
        el = system.find(f"e:{tag}", NS)
        return el.text if el is not None else None

    provider = system.find("e:Provider", NS)
    created = system.find("e:TimeCreated", NS)
    data: dict[str, Any] = {}
    for i, el in enumerate(root.findall("e:EventData/e:Data", NS)):
        data[el.get("Name") or f"param{i + 1}"] = el.text
    return {
        "provider": provider.get("Name") if provider is not None else None,
        "event_id": int(text("EventID") or 0),
        "level": int(text("Level") or 0),
        "time_created": _local(created.get("SystemTime") if created is not None else None),
        "record_id": int(text("EventRecordID") or 0),
        "data": data,
    }


def _local(utc: str | None) -> str | None:
    if not utc:
        return None
    value = utc.rstrip("Z")
    if "." in value:
        head, frac = value.split(".", 1)
        value = f"{head}.{frac[:6]}"
    return datetime.fromisoformat(value + "+00:00").astimezone().isoformat(timespec="seconds")
