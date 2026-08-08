"""Windows boot — call before ``import tkinter`` so the taskbar uses our .exe icon."""
from __future__ import annotations

import os
import sys


def _app_id() -> str:
    if getattr(sys, "frozen", False):
        name = os.path.splitext(os.path.basename(sys.executable))[0]
        return f"EzamAssociates.{name}"
    return "EzamAssociates.CoordinateWizard.Dev"


def apply() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_app_id())
    except Exception:
        pass


apply()
