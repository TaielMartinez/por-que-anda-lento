"""Puertos de lectura cruda hacia Windows.

Todo acceso del Colector al sistema pasa por `Ports`. Cada método devuelve datos
planos serializables a JSON, así las mismas llamadas pueden grabarse como fixtures
(`RecordingPorts`) y reproducirse en los tests (`FixturePorts`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PortError(Exception):
    """El sistema no pudo responder una lectura (sin permisos, herramienta ausente, etc.)."""


class Ports:
    """Interfaz de lectura. Las subclases implementan `_call`."""

    def _call(self, method: str, *args: Any) -> Any:
        raise NotImplementedError

    # --- Comandos y consultas del sistema ---

    def run(self, args: list[str], timeout: float = 120) -> dict[str, Any]:
        """Ejecuta un comando. Devuelve {"returncode", "stdout", "stderr"}."""
        return self._call("run", args, timeout)

    def wmi(self, query: str, namespace: str = "root\\cimv2") -> list[dict[str, Any]]:
        return self._call("wmi", query, namespace)

    def counters(self, paths: list[str]) -> dict[str, Any]:
        """Lee contadores de rendimiento. Un path con comodín devuelve {instancia: valor}."""
        return self._call("counters", paths)

    def registry_values(self, path: str) -> dict[str, Any]:
        return self._call("registry_values", path)

    def registry_subkeys(self, path: str) -> list[str]:
        return self._call("registry_subkeys", path)

    def events(self, log: str, xpath: str, max_events: int) -> list[dict[str, Any]]:
        return self._call("events", log, xpath, max_events)

    # --- Procesos y APIs nativas ---

    def processes(self) -> list[dict[str, Any]]:
        return self._call("processes")

    def process_samples(self) -> list[dict[str, Any]]:
        """Contadores acumulados por proceso para calcular tasas entre muestras."""
        return self._call("process_samples")

    def performance_info(self) -> dict[str, Any]:
        return self._call("performance_info")

    def pool_tags(self) -> list[dict[str, Any]]:
        return self._call("pool_tags")

    def windows(self) -> list[dict[str, Any]]:
        return self._call("windows")

    def connections(self) -> list[dict[str, Any]]:
        return self._call("connections")

    def disks(self) -> list[dict[str, Any]]:
        return self._call("disks")

    def sensors(self) -> list[dict[str, Any]]:
        return self._call("sensors")

    def file_text(self, path: str) -> str:
        return self._call("file_text", path)

    # --- Entorno ---

    def is_admin(self) -> bool:
        return self._call("is_admin")

    def tool_path(self, name: str) -> str | None:
        """Ruta de una herramienta instalada por la Preparación, o None si falta."""
        return self._call("tool_path", name)

    def now(self) -> str:
        """Fecha y hora local en ISO 8601."""
        return self._call("now")

    def monotonic(self) -> float:
        return self._call("monotonic")

    def sleep(self, seconds: float) -> None:
        return self._call("sleep", seconds)


def call_key(method: str, args: tuple[Any, ...]) -> str:
    return f"{method}{json.dumps(list(args), ensure_ascii=False)}"


_NOT_RECORDED = {"sleep"}


class FixturePorts(Ports):
    """Reproduce llamadas grabadas. Una misma llamada repetida devuelve las respuestas
    en orden y, al agotarse, repite la última. Una llamada no grabada es un PortError."""

    def __init__(self, calls: dict[str, list[Any]]):
        self.calls = {k: list(v) for k, v in calls.items()}
        self._cursor: dict[str, int] = {}

    @classmethod
    def load(cls, *paths: Path) -> FixturePorts:
        calls: dict[str, list[Any]] = {}
        for path in paths:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for key, responses in data["calls"].items():
                calls.setdefault(key, []).extend(responses)
        return cls(calls)

    def set(self, method: str, *args: Any, response: Any) -> None:
        """Reemplaza la respuesta de una llamada (para variar un escenario en un test)."""
        self.calls[call_key(method, args)] = [response]

    def fail(self, method: str, *args: Any, reason: str = "no disponible") -> None:
        self.calls[call_key(method, args)] = [{"__error__": reason}]

    def _call(self, method: str, *args: Any) -> Any:
        if method in _NOT_RECORDED:
            return None
        key = call_key(method, args)
        responses = self.calls.get(key)
        if not responses:
            raise PortError(f"sin fixture para {key}")
        i = self._cursor.get(key, 0)
        self._cursor[key] = i + 1
        response = responses[min(i, len(responses) - 1)]
        if isinstance(response, dict) and "__error__" in response:
            raise PortError(response["__error__"])
        return json.loads(json.dumps(response))


class RecordingPorts(Ports):
    """Envuelve puertos reales y graba cada llamada para generar fixtures."""

    def __init__(self, inner: Ports):
        self.inner = inner
        self.calls: dict[str, list[Any]] = {}

    def _call(self, method: str, *args: Any) -> Any:
        if method in _NOT_RECORDED:
            return self.inner._call(method, *args)
        key = call_key(method, args)
        try:
            result = self.inner._call(method, *args)
        except PortError as e:
            self.calls.setdefault(key, []).append({"__error__": str(e)})
            raise
        self.calls.setdefault(key, []).append(json.loads(json.dumps(result, default=str)))
        return result

    def save(self, path: Path) -> None:
        Path(path).write_text(
            json.dumps({"calls": self.calls}, ensure_ascii=False, indent=1), encoding="utf-8"
        )
