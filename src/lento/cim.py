"""Conversión de fechas CIM (WMI) e ISO."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_cim_datetime(value: str | None) -> datetime | None:
    """'20260927083012.500000-180' -> datetime con zona horaria."""
    if not value or len(value) < 14:
        return None
    try:
        base = datetime.strptime(value[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None
    offset_min = 0
    if len(value) >= 25 and value[21] in "+-":
        try:
            offset_min = int(value[22:25]) * (-1 if value[21] == "-" else 1)
        except ValueError:
            offset_min = 0
    return base.replace(tzinfo=timezone(timedelta(minutes=offset_min)))


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)
