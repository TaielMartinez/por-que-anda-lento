"""Auto-elevación por UAC (ADR 0002).

El proceso sin privilegios relanza el Colector con el verbo "runas", espera a que
termine y lee la ruta de la Captura desde un archivo de resultado.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path
from typing import Any

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWMINNOACTIVE = 7
ERROR_CANCELLED = 1223
INFINITE = 0xFFFFFFFF


class ElevationCancelled(Exception):
    """El usuario rechazó el pedido de UAC."""


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def is_admin() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def run_elevated(module_args: list[str]) -> tuple[int, dict[str, Any]]:
    """Ejecuta `python -m lento.cli <module_args> --result-file X` elevado y espera.

    Devuelve (código de salida, contenido del archivo de resultado)."""
    fd, result_path = tempfile.mkstemp(prefix="lento-", suffix=".json")
    os.close(fd)
    try:
        params = subprocess.list2cmdline(["-m", "lento.cli", *module_args, "--result-file", result_path])
        info = _SHELLEXECUTEINFOW()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "runas"
        info.lpFile = sys.executable
        info.lpParameters = params
        info.lpDirectory = os.getcwd()
        info.nShow = SW_SHOWMINNOACTIVE
        if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
            error = ctypes.GetLastError()
            if error == ERROR_CANCELLED:
                raise ElevationCancelled()
            raise OSError(error, "ShellExecuteExW falló")
        kernel32 = ctypes.windll.kernel32
        kernel32.WaitForSingleObject(info.hProcess, INFINITE)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        kernel32.CloseHandle(info.hProcess)
        text = Path(result_path).read_text(encoding="utf-8").strip()
        return code.value, json.loads(text) if text else {}
    finally:
        Path(result_path).unlink(missing_ok=True)
