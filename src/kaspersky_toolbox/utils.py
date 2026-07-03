"""Low-level Windows utilities: registry, admin check, file ops, process check."""

import os
import sys
import glob
import ctypes
import winreg
from ctypes import wintypes

import psutil

# ── Win32 DLLs ──────────────────────────────────────────────────────────────

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

kernel32.GetCurrentProcess.argtypes = ()
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL

advapi32.OpenProcessToken.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
)
advapi32.OpenProcessToken.restype = wintypes.BOOL

advapi32.GetTokenInformation.argtypes = (
    wintypes.HANDLE,
    ctypes.c_uint,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
)
advapi32.GetTokenInformation.restype = wintypes.BOOL

# ── Registry path constants ─────────────────────────────────────────────────

AVP_BASE = r"SOFTWARE\WOW6432Node\KasperskyLab"
KES_BASE = r"SOFTWARE\WOW6432Node\KasperskyLab\protected"
SOFTWARE_WOW = r"SOFTWARE\WOW6432Node"

# ── Admin elevation ─────────────────────────────────────────────────────────


def is_admin() -> bool:
    """Return ``True`` if the current process is running elevated."""
    try:
        TOKEN_QUERY = 0x0008
        TokenElevation = 20

        handle: wintypes.HANDLE = kernel32.GetCurrentProcess()
        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return False

        token_information = ctypes.c_uint32(0)
        needed = ctypes.c_uint32(0)

        result = advapi32.GetTokenInformation(
            token,
            TokenElevation,
            ctypes.byref(token_information),
            ctypes.sizeof(token_information),
            ctypes.byref(needed),
        )
        kernel32.CloseHandle(token)
        return result != 0 and token_information.value != 0
    except Exception:
        return False


def run_as_admin() -> None:
    """Re-launch the current script with administrator privileges, then exit."""
    script = sys.argv[0]
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}"', None, 1
    )
    sys.exit(0)


# ── Registry helpers ────────────────────────────────────────────────────────


def get_registry_value(base_path: str, subkey_path: str, value_name: str):
    """Read a value from ``HKLM\\{base_path}\\{subkey_path}``.

    Returns the value, or ``None`` if the path does not exist.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"{base_path}\\{subkey_path}",
            0,
            winreg.KEY_READ,
        )
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return None


def set_registry_value(
    base_path: str,
    subkey_path: str,
    value_name: str,
    value,
    reg_type: int = winreg.REG_DWORD,
) -> bool:
    """Write a value to ``HKLM\\{base_path}\\{subkey_path}``.

    Returns ``True`` on success, ``False`` on failure.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"{base_path}\\{subkey_path}",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(key, value_name, 0, reg_type, value)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


# ── File helpers ────────────────────────────────────────────────────────────


def delete_files(path_pattern: str) -> None:
    """Delete all files matching a glob pattern, ignoring individual errors."""
    for path in glob.glob(path_pattern):
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception:
                pass


def get_vbs_path() -> str:
    """Resolve the absolute path to the embedded ``act.vbs``.

    In development the file lives beside this module in the package directory.
    In PyInstaller frozen builds it is extracted alongside the executable or
    in ``sys._MEIPASS``.
    """
    if getattr(sys, "frozen", False):
        base_dir = (
            sys._MEIPASS
            if hasattr(sys, "_MEIPASS")
            else os.path.dirname(sys.executable)
        )
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "act.vbs")


# ── Process helpers ─────────────────────────────────────────────────────────


def check_process_running(process_name: str) -> bool:
    """Return ``True`` if at least one process with *process_name* is running."""
    return any(
        proc.info["name"] == process_name for proc in psutil.process_iter(["name"])
    )


def get_base_path_for_version(version_key: str) -> str:
    """Return the registry base path for a given Kaspersky version key."""
    if version_key.startswith("AVP"):
        return AVP_BASE
    elif version_key.startswith("KES"):
        return KES_BASE
    return AVP_BASE
