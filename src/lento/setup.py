"""Preparación: descarga, verifica e instala las herramientas externas (ADR 0003).

Es lo único del proyecto que modifica el sistema. Idempotente: lo ya instalado se saltea
y lo ya descargado con el hash correcto no se vuelve a bajar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from lento.tools import TOOLS, TOOLS_BY_NAME, Tool, installed_path
from lento.windows import TOOLS_DIR

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UAC_CANCELLED = 2
EXIT_NEEDS_CONSENT = 3

REBOOT_REQUIRED = 3010


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="setup", description="Preparación: instala las herramientas externas.")
    p.add_argument("--yes", action="store_true", help="aceptar las licencias de las herramientas sin preguntar")
    p.add_argument("--only", help="instalar solo estas herramientas (separadas por coma)")
    p.add_argument("--status", action="store_true", help="mostrar qué está instalado y salir")
    p.add_argument("--result-file", type=Path, help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    tools = _selected(args.only)
    if args.status:
        for tool in tools:
            path = installed_path(tool.name, TOOLS_DIR)
            print(f"{'OK   ' if path else 'FALTA'} {tool.name:22} {tool.description}")
        return EXIT_OK

    pending = [t for t in tools if installed_path(t.name, TOOLS_DIR) is None]
    if not pending:
        _emit(args, {"results": [{"tool": t.name, "status": "already_installed"} for t in tools]})
        return EXIT_OK

    from lento import elevation

    if not elevation.is_admin():
        if not args.yes and not _consent(pending):
            return EXIT_NEEDS_CONSENT
        forwarded = ["setup", "--yes", *(["--only", args.only] if args.only else [])]
        print("Pidiendo permisos de administrador (UAC)...", file=sys.stderr)
        try:
            code, result = elevation.run_elevated(forwarded)
        except elevation.ElevationCancelled:
            print("Se rechazó el pedido de UAC: la Preparación necesita admin.", file=sys.stderr)
            return EXIT_UAC_CANCELLED
        _print_results(result)
        return code

    if not args.yes and not args.result_file and not _consent(pending):
        return EXIT_NEEDS_CONSENT
    results = [_install(t) for t in tools]
    _emit(args, {"results": results})
    return EXIT_OK if all(r["status"] != "failed" for r in results) else EXIT_FAILED


def _selected(only: str | None) -> list[Tool]:
    if not only:
        return TOOLS
    names = [n.strip() for n in only.split(",") if n.strip()]
    unknown = [n for n in names if n not in TOOLS_BY_NAME]
    if unknown:
        raise SystemExit(f"Herramientas desconocidas: {', '.join(unknown)}. Válidas: {', '.join(TOOLS_BY_NAME)}")
    return [TOOLS_BY_NAME[n] for n in names]


def _consent(pending: list[Tool]) -> bool:
    print("La Preparación va a descargar e instalar (fuentes oficiales, versión fijada, SHA256 verificado):")
    for t in pending:
        print(f"  - {t.description} [{t.version}] — licencia: {t.license}")
    print("Instalar implica aceptar esas licencias. PawnIO instala un driver de kernel.")
    if not sys.stdin.isatty():
        print("Sin terminal interactiva: repetir con --yes para aceptar.", file=sys.stderr)
        return False
    try:
        answer = input("¿Continuar? [s/N] ")
    except EOFError:
        print("\nSin respuesta: repetir con --yes para aceptar.", file=sys.stderr)
        return False
    return answer.strip().lower() in ("s", "si", "sí", "y", "yes")


def _install(tool: Tool) -> dict[str, Any]:
    if installed_path(tool.name, TOOLS_DIR):
        return {"tool": tool.name, "status": "already_installed"}
    try:
        package = _download(tool)
        if tool.kind == "zip":
            _extract(tool, package)
        else:
            code = subprocess.run([str(package), *tool.install_args]).returncode
            if code not in (0, REBOOT_REQUIRED):
                raise RuntimeError(f"el instalador terminó con código {code}")
        if installed_path(tool.name, TOOLS_DIR) is None:
            raise RuntimeError("terminó sin errores pero no se encuentra lo instalado")
        return {"tool": tool.name, "status": "installed", "reboot_required": tool.kind == "installer" and code == REBOOT_REQUIRED}
    except Exception as e:  # noqa: BLE001 - una herramienta que falla no frena a las demás
        return {"tool": tool.name, "status": "failed", "error": f"{type(e).__name__}: {e}"}


def _download(tool: Tool) -> Path:
    target = TOOLS_DIR / "_downloads" / tool.filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and _sha256(target) == tool.sha256:
        return target
    request = urllib.request.Request(tool.url, headers={"User-Agent": "por-que-anda-lento-setup"})
    with urllib.request.urlopen(request, timeout=300) as response, open(target, "wb") as f:
        while chunk := response.read(1 << 20):
            f.write(chunk)
    actual = _sha256(target)
    if actual != tool.sha256:
        target.unlink()
        raise RuntimeError(
            f"el SHA256 no coincide (esperado {tool.sha256}, obtenido {actual}). "
            "La fuente publicó otra versión: actualizar version/url/sha256 en lento/tools.py a mano."
        )
    return target


def _extract(tool: Tool, package: Path) -> None:
    dest = TOOLS_DIR / tool.folder
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as z:
        if not tool.extract:
            z.extractall(dest)
            return
        for name in tool.extract:
            (dest / Path(name).name).write_bytes(z.read(name))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _emit(args: argparse.Namespace, result: dict[str, Any]) -> None:
    if args.result_file:
        args.result_file.write_text(json.dumps(result), encoding="utf-8")
    else:
        _print_results(result)


def _print_results(result: dict[str, Any]) -> None:
    labels = {"installed": "instalada", "already_installed": "ya estaba", "failed": "FALLÓ"}
    for r in result.get("results", []):
        line = f"{labels.get(r['status'], r['status']):10} {r['tool']}"
        if r.get("error"):
            line += f": {r['error']}"
        if r.get("reboot_required"):
            line += " (requiere reiniciar)"
        print(line)
    if "error" in result:
        print(f"La Preparación falló: {result['error']}", file=sys.stderr)
