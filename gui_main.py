#!/usr/bin/env python3
"""Entry point for flchemist GUI — replaces the old wizard with phase-based dialogs."""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in path
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Configure logging BEFORE any Qt imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("flchemist.gui_main")
log.info("Starting flchemist GUI")

# Set Qt platform plugin path before importing PyQt6
_pyqt6_dir = Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6"
_plugin_dir = _pyqt6_dir / "Qt6" / "plugins"
if _plugin_dir.is_dir():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(_plugin_dir)
    log.info("QT_QPA_PLATFORM_PLUGIN_PATH=%s", str(_plugin_dir))
_dll_dir = str(_pyqt6_dir)
os.environ["PATH"] = _dll_dir + os.pathsep + os.environ.get("PATH", "")
log.info("PyQt6 DLL dir prepended to PATH: %s", _dll_dir)

# Set global exception hook to catch Python-level crashes
_orig_excepthook = sys.excepthook

def _exception_hook(exc_type, exc_value, exc_tb):
    log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    _orig_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = _exception_hook

from PyQt6 import QtWidgets, QtGui
log.info("PyQt6 imported")

from gui.main_window import MainWindow
from gui.theme import dark_stylesheet
log.info("MainWindow imported")

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(dark_stylesheet())
    log.info("QApplication created, dark theme applied")
    app.setApplicationName("flchemist")
    app.setApplicationDisplayName("flchemist")
    app.setWindowIcon(QtGui.QIcon(str(Path(__file__).resolve().parent / "flchemist.ico")))

    window = MainWindow()
    window.show()
    log.info("MainWindow shown, entering event loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        log.exception("Fatal error in GUI main")
        raise
