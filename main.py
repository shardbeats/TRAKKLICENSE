"""TRAKKLICENSE entry point."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.utils.crash import install_crash_handler
from app.utils.paths import base_dir
from app.version import __version__

# In a one-file exe, __file__ lives inside a temp dir (sys._MEIPASS) that is
# deleted on exit and must never hold writable data. base_dir() already
# resolves next to the exe when frozen / %APPDATA% from source.
IS_FROZEN = bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))


def main():
    # Windowed frozen exes have stdout=None: redirect + hook crashes first,
    # so no failure is ever silent (details in <base>/error.log).
    install_crash_handler(base_dir())
    app = QApplication(sys.argv)
    app.setApplicationName("TRAKKLICENSE")
    app.setApplicationVersion(__version__)
    try:
        from app.utils.paths import styles_path
        qss = styles_path()
    except Exception:
        qss = Path(__file__).resolve().parent / "app" / "ui" / "styles.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
