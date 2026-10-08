"""PyInstaller runtime hook — must run before pyi_rth__tkinter (alphabetical order)."""
import os
import sys

if sys.platform == "win32":
    try:
        import ctypes

        if getattr(sys, "frozen", False):
            name = os.path.splitext(os.path.basename(sys.executable))[0]
            app_id = f"EzamAssociates.{name}"
        else:
            app_id = "EzamAssociates.CoordinateWizard.Dev"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass
