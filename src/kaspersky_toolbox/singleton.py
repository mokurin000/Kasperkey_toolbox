"""Application singleton guard using a named Win32 mutex."""

import sys
import ctypes
from ctypes import wintypes


class SingletonGuard:
    """Context manager that ensures only one instance of the application runs.

    Uses a named Win32 mutex in the ``Global\\`` namespace. If another instance
    already holds the mutex, the process exits immediately.

    Usage::

        with SingletonGuard():
            ...
    """

    def __init__(self, mutex_name: str = "Global\\KasperskyToolboxMutex") -> None:
        self._mutex_name = mutex_name
        self._handle: wintypes.HANDLE | None = None

    def __enter__(self) -> "SingletonGuard":
        self._handle = ctypes.windll.kernel32.CreateMutexA(
            None, 1, self._mutex_name.encode()
        )
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            sys.exit(0)
        return self

    def __exit__(self, *args: object) -> None:
        if self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None
