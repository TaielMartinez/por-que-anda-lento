"""Puntos de entrada: `collect` (Colector), `setup` (Preparación) y `record-fixture` (desarrollo)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from lento.collector import CollectOptions, collect

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPTURES_DIR = PROJECT_ROOT / "captures"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_UAC_CANCELLED = 2


def _collect_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="collect", description="Toma una Captura del estado de la PC.")
    p.add_argument("--duration", type=float, default=60, help="segundos de la Ventana de muestreo (60)")
    p.add_argument("--interval", type=float, default=1, help="segundos entre muestras (1)")
    p.add_argument("--reference", action="store_true", help="marcar la Captura como Referencia (la PC anda bien)")
    p.add_argument("--keep-etl", action="store_true", help="conservar la traza ETW cruda")
    p.add_argument("--out", type=Path, default=CAPTURES_DIR, help="carpeta de Capturas")
    p.add_argument("--result-file", type=Path, help=argparse.SUPPRESS)
    return p


def collect_main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = _collect_parser().parse_args(argv)
    from lento import elevation

    if not elevation.is_admin():
        if args.result_file:
            print("El Colector necesita permisos de administrador.", file=sys.stderr)
            return EXIT_FAILED
        forwarded = [a for a in argv]
        if "--out" not in forwarded:
            forwarded += ["--out", str(args.out.resolve())]
        print("Pidiendo permisos de administrador (UAC)...", file=sys.stderr)
        try:
            code, result = elevation.run_elevated(["collect", *forwarded])
        except elevation.ElevationCancelled:
            print("Se rechazó el pedido de UAC: el Colector necesita admin (ver docs/adr/0002).", file=sys.stderr)
            return EXIT_UAC_CANCELLED
        return _report(code, result)

    try:
        from lento.windows import WindowsPorts

        path = collect(WindowsPorts(), args.out, _options(args))
        result = {"capture": str(path)}
        code = EXIT_OK
    except Exception as e:  # noqa: BLE001 - se informa al proceso que lanzó la elevación
        result = {"error": f"{type(e).__name__}: {e}"}
        code = EXIT_FAILED
    if args.result_file:
        args.result_file.write_text(json.dumps(result), encoding="utf-8")
        return code
    return _report(code, result)


def _options(args: argparse.Namespace) -> CollectOptions:
    return CollectOptions(
        duration_s=args.duration,
        interval_s=args.interval,
        reference=args.reference,
        keep_etl=args.keep_etl,
    )


def _report(code: int, result: dict) -> int:
    if "capture" in result:
        print(result["capture"])
        return code
    print(f"El Colector falló: {result.get('error', 'sin detalle')}", file=sys.stderr)
    return code or EXIT_FAILED


def setup_main(argv: list[str] | None = None) -> int:
    from lento.setup import main

    return main(sys.argv[1:] if argv is None else argv)


def record_main(argv: list[str] | None = None) -> int:
    """Graba las llamadas a los puertos de una Captura real como fixture de tests."""
    p = argparse.ArgumentParser(prog="record-fixture")
    p.add_argument("name", help="nombre del fixture (tests/fixtures/<name>.json)")
    p.add_argument("--domains", required=True, help="dominios a ejecutar, separados por coma")
    p.add_argument("--duration", type=float, default=0)
    p.add_argument("--interval", type=float, default=1)
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    from lento.ports import RecordingPorts
    from lento.windows import WindowsPorts

    ports = RecordingPorts(WindowsPorts())
    options = CollectOptions(
        duration_s=args.duration, interval_s=args.interval, only=args.domains.split(",")
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = collect(ports, Path(tmp), options)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    target = PROJECT_ROOT / "tests" / "fixtures" / f"{args.name}.json"
    ports.save(target)
    print(json.dumps(manifest["domains"], ensure_ascii=False, indent=1))
    print(f"fixture: {target}")
    return EXIT_OK


if __name__ == "__main__":
    command, *rest = sys.argv[1:] or ["collect"]
    entry = {"collect": collect_main, "setup": setup_main, "record-fixture": record_main}[command]
    sys.exit(entry(rest))
