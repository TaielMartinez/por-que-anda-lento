"""Implementación real de los puertos sobre Windows (psutil, WMI, PDH, registro, ctypes).

Este módulo es el adaptador hacia el sistema: no tiene lógica de dominio y no se
testea con fixtures; se valida con la prueba de humo.
"""

from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any

from lento.ports import PortError, Ports

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"


class WindowsPorts(Ports):
    def __init__(self, tools_dir: Path = TOOLS_DIR):
        self.tools_dir = tools_dir
        self._queries: dict[tuple[str, ...], Any] = {}

    def _call(self, method: str, *args: Any) -> Any:
        impl = getattr(self, f"_{method}", None)
        if impl is None:
            raise PortError(f"puerto no implementado: {method}")
        try:
            return impl(*args)
        except PortError:
            raise
        except Exception as e:  # noqa: BLE001 - toda falla del sistema se vuelve PortError
            raise PortError(f"{type(e).__name__}: {e}") from e

    # --- Comandos y consultas ---

    def _run(self, args: list[str], timeout: float) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except FileNotFoundError as e:
            raise PortError(f"comando no encontrado: {args[0]}") from e
        return {
            "returncode": proc.returncode,
            "stdout": _decode(proc.stdout),
            "stderr": _decode(proc.stderr),
        }

    def _wmi(self, query: str, namespace: str) -> list[dict[str, Any]]:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            service = win32com.client.GetObject(f"winmgmts:{{impersonationLevel=impersonate}}!\\\\.\\{namespace}")
            rows = []
            for obj in service.ExecQuery(query):
                rows.append({p.Name: _plain(p.Value) for p in obj.Properties_})
            return rows
        finally:
            pythoncom.CoUninitialize()

    def _counters(self, paths: list[str]) -> dict[str, Any]:
        import win32pdh

        key = tuple(paths)
        query = self._queries.get(key)
        if query is None:
            handle = win32pdh.OpenQuery()
            counters: dict[str, Any] = {}
            for p in paths:
                try:
                    counters[p] = win32pdh.AddEnglishCounter(handle, p)
                except Exception:  # noqa: BLE001 - contador inexistente en esta PC
                    counters[p] = None
            win32pdh.CollectQueryData(handle)
            time.sleep(0.5)  # los contadores de tasa necesitan dos lecturas
            query = (handle, counters)
            self._queries[key] = query
        handle, counters = query
        win32pdh.CollectQueryData(handle)
        values: dict[str, Any] = {}
        for p, h in counters.items():
            if h is None:
                values[p] = None
                continue
            try:
                if "*" in p:
                    values[p] = dict(win32pdh.GetFormattedCounterArray(h, win32pdh.PDH_FMT_DOUBLE))
                else:
                    values[p] = win32pdh.GetFormattedCounterValue(h, win32pdh.PDH_FMT_DOUBLE)[1]
            except Exception:  # noqa: BLE001 - instancia desaparecida o sin datos
                values[p] = None
        return values

    def _registry_values(self, path: str) -> dict[str, Any]:
        import winreg

        with _open_key(path) as key:
            values = {}
            i = 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(key, i)
                except OSError:
                    break
                values[name] = value.hex() if isinstance(value, bytes) else value
                i += 1
            return values

    def _registry_subkeys(self, path: str) -> list[str]:
        import winreg

        with _open_key(path) as key:
            names = []
            i = 0
            while True:
                try:
                    names.append(winreg.EnumKey(key, i))
                except OSError:
                    break
                i += 1
            return names

    def _events(self, log: str, xpath: str, max_events: int) -> list[dict[str, Any]]:
        import win32evtlog

        from lento.eventxml import parse_event_xml

        flags = win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection
        handle = win32evtlog.EvtQuery(log, flags, xpath)
        events: list[dict[str, Any]] = []
        while len(events) < max_events:
            batch = win32evtlog.EvtNext(handle, min(100, max_events - len(events)))
            if not batch:
                break
            for ev in batch:
                xml = win32evtlog.EvtRender(ev, win32evtlog.EvtRenderEventXml)
                event = parse_event_xml(xml)
                try:
                    meta = win32evtlog.EvtOpenPublisherMetadata(event["provider"])
                    event["message"] = win32evtlog.EvtFormatMessage(
                        meta, ev, win32evtlog.EvtFormatMessageEvent
                    )
                except Exception:  # noqa: BLE001 - proveedor sin mensajes registrados
                    event["message"] = None
                events.append(event)
        return events

    # --- Procesos y APIs nativas ---

    def _processes(self) -> list[dict[str, Any]]:
        import psutil

        attrs = [
            "pid", "ppid", "name", "exe", "cmdline", "username", "create_time", "status",
            "num_threads", "num_handles", "cpu_times", "memory_info", "io_counters", "nice",
        ]
        rows = []
        for proc in psutil.process_iter(attrs, ad_value=None):
            info = proc.info
            mem = info.pop("memory_info")
            cpu = info.pop("cpu_times")
            io = info.pop("io_counters")
            info["working_set_bytes"] = getattr(mem, "wset", None)
            info["peak_working_set_bytes"] = getattr(mem, "peak_wset", None)
            info["private_bytes"] = getattr(mem, "private", None)
            info["paged_pool_bytes"] = getattr(mem, "paged_pool", None)
            info["nonpaged_pool_bytes"] = getattr(mem, "nonpaged_pool", None)
            info["cpu_user_s"] = getattr(cpu, "user", None)
            info["cpu_system_s"] = getattr(cpu, "system", None)
            info["io_read_bytes"] = getattr(io, "read_bytes", None)
            info["io_write_bytes"] = getattr(io, "write_bytes", None)
            info["io_read_count"] = getattr(io, "read_count", None)
            info["io_write_count"] = getattr(io, "write_count", None)
            info["io_other_bytes"] = getattr(io, "other_bytes", None)
            info["priority"] = info.pop("nice")
            rows.append(info)
        return rows

    def _process_samples(self) -> list[dict[str, Any]]:
        import psutil

        rows = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_times", "memory_info", "io_counters"], ad_value=None
        ):
            info = proc.info
            cpu, mem, io = info["cpu_times"], info["memory_info"], info["io_counters"]
            rows.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu_s": (cpu.user + cpu.system) if cpu else None,
                "private_bytes": getattr(mem, "private", None),
                "working_set_bytes": getattr(mem, "wset", None),
                "io_read_bytes": getattr(io, "read_bytes", None),
                "io_write_bytes": getattr(io, "write_bytes", None),
            })
        return rows

    def _performance_info(self) -> dict[str, Any]:
        info = _PERFORMANCE_INFORMATION()
        info.cb = ctypes.sizeof(info)
        if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
            raise PortError("GetPerformanceInfo falló")
        page = info.PageSize
        return {
            "page_size": page,
            "commit_total_bytes": info.CommitTotal * page,
            "commit_limit_bytes": info.CommitLimit * page,
            "commit_peak_bytes": info.CommitPeak * page,
            "physical_total_bytes": info.PhysicalTotal * page,
            "physical_available_bytes": info.PhysicalAvailable * page,
            "system_cache_bytes": info.SystemCache * page,
            "kernel_total_bytes": info.KernelTotal * page,
            "kernel_paged_bytes": info.KernelPaged * page,
            "kernel_nonpaged_bytes": info.KernelNonpaged * page,
            "handle_count": info.HandleCount,
            "process_count": info.ProcessCount,
            "thread_count": info.ThreadCount,
        }

    def _pool_tags(self) -> list[dict[str, Any]]:
        ntdll = ctypes.windll.ntdll
        size = 1 << 20
        while True:
            buf = ctypes.create_string_buffer(size)
            needed = wintypes.ULONG()
            status = ntdll.NtQuerySystemInformation(22, buf, size, ctypes.byref(needed)) & 0xFFFFFFFF
            if status == 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH
                size = max(size * 2, needed.value + 4096)
                continue
            if status != 0:
                raise PortError(f"NtQuerySystemInformation(SystemPoolTagInformation) = 0x{status:08X}")
            break
        count = ctypes.cast(buf, ctypes.POINTER(wintypes.ULONG))[0]
        entries = ctypes.cast(
            ctypes.addressof(buf) + ctypes.sizeof(ctypes.c_size_t), ctypes.POINTER(_SYSTEM_POOLTAG)
        )
        tags = []
        for i in range(count):
            e = entries[i]
            tags.append({
                "tag": bytes(e.Tag).decode("latin-1"),
                "paged_allocs": e.PagedAllocs,
                "paged_frees": e.PagedFrees,
                "paged_bytes": e.PagedUsed,
                "nonpaged_allocs": e.NonPagedAllocs,
                "nonpaged_frees": e.NonPagedFrees,
                "nonpaged_bytes": e.NonPagedUsed,
            })
        return tags

    def _windows(self) -> list[dict[str, Any]]:
        user32 = ctypes.windll.user32
        foreground = user32.GetForegroundWindow()
        rows: list[dict[str, Any]] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd: int, _: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            rows.append({
                "pid": pid.value,
                "title": title.value,
                "foreground": hwnd == foreground,
                "minimized": bool(user32.IsIconic(hwnd)),
            })
            return True

        user32.EnumWindows(callback, 0)
        return rows

    def _connections(self) -> list[dict[str, Any]]:
        import psutil

        rows = []
        for c in psutil.net_connections(kind="inet"):
            rows.append({
                "pid": c.pid,
                "protocol": "tcp" if c.type == 1 else "udp",
                "family": "ipv6" if c.family == 23 else "ipv4",
                "local_address": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                "remote_address": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                "status": c.status,
            })
        return rows

    def _disks(self) -> list[dict[str, Any]]:
        import psutil

        rows = []
        for part in psutil.disk_partitions(all=False):
            row: dict[str, Any] = {
                "mountpoint": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype,
                "opts": part.opts,
            }
            try:
                usage = psutil.disk_usage(part.mountpoint)
                row.update(total_bytes=usage.total, used_bytes=usage.used, free_bytes=usage.free)
            except OSError as e:
                row["error"] = str(e)
            rows.append(row)
        return rows

    def _sensors(self) -> list[dict[str, Any]]:
        from lento.lhm import read_sensors

        dll = self._tool_path("librehardwaremonitor")
        if dll is None:
            raise PortError("LibreHardwareMonitor no está instalado (correr la Preparación)")
        return read_sensors(Path(dll))

    def _file_text(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise PortError(str(e)) from e

    # --- Entorno ---

    def _is_admin(self) -> bool:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())

    def _tool_path(self, name: str) -> str | None:
        from lento.tools import installed_path

        path = installed_path(name, self.tools_dir)
        return str(path) if path else None

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _monotonic(self) -> float:
        return time.monotonic()

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


def _decode(data: bytes) -> str:
    oem = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    for encoding in ("utf-8", oem):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _plain(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


_HIVES = {
    "HKLM": "HKEY_LOCAL_MACHINE",
    "HKCU": "HKEY_CURRENT_USER",
    "HKU": "HKEY_USERS",
    "HKCR": "HKEY_CLASSES_ROOT",
}


def _open_key(path: str) -> Any:
    import winreg

    hive_name, _, sub = path.partition("\\")
    hive = getattr(winreg, _HIVES.get(hive_name, hive_name))
    try:
        return winreg.OpenKey(hive, sub, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    except FileNotFoundError as e:
        raise PortError(f"clave de registro inexistente: {path}") from e


class _PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", wintypes.DWORD),
        ("ProcessCount", wintypes.DWORD),
        ("ThreadCount", wintypes.DWORD),
    ]


class _SYSTEM_POOLTAG(ctypes.Structure):
    _fields_ = [
        ("Tag", ctypes.c_ubyte * 4),
        ("PagedAllocs", wintypes.ULONG),
        ("PagedFrees", wintypes.ULONG),
        ("PagedUsed", ctypes.c_size_t),
        ("NonPagedAllocs", wintypes.ULONG),
        ("NonPagedFrees", wintypes.ULONG),
        ("NonPagedUsed", ctypes.c_size_t),
    ]
