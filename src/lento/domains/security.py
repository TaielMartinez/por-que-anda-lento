"""Dominio security: estado de Defender (¿está escaneando?), exclusiones y antivirus instalados."""

from __future__ import annotations

from typing import Any

from lento.capture import DomainWriter
from lento.cim import iso, parse_cim_datetime
from lento.ports import PortError, Ports

NAME = "security"
BASE = "snapshot/security"
DOC = "security"

DEFENDER_NS = "root\\Microsoft\\Windows\\Defender"
DEFENDER_STATUS_QUERY = (
    "SELECT AMRunningMode, AntivirusEnabled, RealTimeProtectionEnabled, QuickScanStartTime, QuickScanEndTime, "
    "FullScanStartTime, FullScanEndTime, AntivirusSignatureAge FROM MSFT_MpComputerStatus"
)
DEFENDER_PREFS_QUERY = "SELECT ExclusionPath, ExclusionProcess, ExclusionExtension FROM MSFT_MpPreference"
AV_NS = "root\\SecurityCenter2"
AV_QUERY = "SELECT displayName, productState, pathToSignedProductExe FROM AntiVirusProduct"


def collect(ports: Ports, out: DomainWriter) -> None:
    status: dict[str, Any] | None = None
    reason = None
    try:
        rows = ports.wmi(DEFENDER_STATUS_QUERY, DEFENDER_NS)
        status = _status(rows[0]) if rows else None
    except PortError as e:
        reason = str(e)
    out.json("defender_status", status, "¿Defender está activo y está escaneando ahora?", reason)

    exclusions: dict[str, Any] = {}
    reason = None
    try:
        prefs = ports.wmi(DEFENDER_PREFS_QUERY, DEFENDER_NS)
        p = prefs[0] if prefs else {}
        exclusions = {
            "paths": p.get("ExclusionPath") or [],
            "processes": p.get("ExclusionProcess") or [],
            "extensions": p.get("ExclusionExtension") or [],
        }
    except PortError as e:
        reason = str(e)
    out.json("defender_exclusions", exclusions, "¿Qué rutas, procesos y extensiones excluye Defender?", reason)

    products: list[dict[str, Any]] = []
    reason = None
    try:
        products = [_product(p) for p in ports.wmi(AV_QUERY, AV_NS)]
    except PortError as e:
        reason = str(e)
    out.json("antivirus_products", products, "¿Qué antivirus están registrados y cuáles están activos?", reason)

    out.summary().update(
        defender_realtime=status["realtime_protection"] if status else None,
        defender_scan_in_progress=status["scan_in_progress"] if status else None,
        antivirus_active=[p["name"] for p in products if p["enabled"]],
    )


def _status(row: dict[str, Any]) -> dict[str, Any]:
    quick_start, quick_end = parse_cim_datetime(row.get("QuickScanStartTime")), parse_cim_datetime(row.get("QuickScanEndTime"))
    full_start, full_end = parse_cim_datetime(row.get("FullScanStartTime")), parse_cim_datetime(row.get("FullScanEndTime"))
    in_progress = None
    if full_start and (not full_end or full_start > full_end):
        in_progress = "full"
    elif quick_start and (not quick_end or quick_start > quick_end):
        in_progress = "quick"
    return {
        "running_mode": row.get("AMRunningMode"),
        "antivirus_enabled": row.get("AntivirusEnabled"),
        "realtime_protection": row.get("RealTimeProtectionEnabled"),
        "scan_in_progress": in_progress,
        "last_quick_scan": {"start": iso(quick_start), "end": iso(quick_end)},
        "last_full_scan": {"start": iso(full_start), "end": iso(full_end)},
        "signature_age_days": row.get("AntivirusSignatureAge"),
    }


def _product(p: dict[str, Any]) -> dict[str, Any]:
    state = p.get("productState") or 0
    return {
        "name": p.get("displayName"),
        "enabled": (state >> 12) & 0xF == 1,
        "definitions_up_to_date": (state >> 4) & 0xF == 0,
        "product_state": state,
        "executable": p.get("pathToSignedProductExe"),
    }
