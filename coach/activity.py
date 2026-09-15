"""Reads the foreground program name (design.md, section 4 — privacy).

ONLY the process name is read (e.g. "chrome.exe"). Never window titles,
never document names, never content. Windows-only; returns "" elsewhere so
the classifier degrades to "unknown" instead of crashing.
"""
import sys


def get_foreground_program_name() -> str:
    """Return the process name of the window currently in front, or ''."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
        import psutil

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""

        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""

        return psutil.Process(pid.value).name().lower()
    except Exception as e:
        print(f"[DEBUG] Foreground program lookup failed: {e}")
        return ""
