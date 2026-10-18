"""Frozen crash handling (TRAKKOUT pattern, adapted: no network/ssl here).

A windowed PyInstaller exe has sys.stdout=None: unhandled exceptions die
silently. This redirects stdio to a log file and installs a sys.excepthook
that records the traceback and shows a dialog. Safe to call from source too
(log next to data dir); never raises.
"""
import datetime
import os
import sys
import traceback
from pathlib import Path


def error_log_path(base_dir: Path) -> Path:
    return base_dir / "error.log"


def install_crash_handler(base_dir: Path):
    """Redirect stdout/stderr to trakklicense.log + hook uncaught exceptions.

    Returns the error.log path. The dialog is skipped offscreen (tests) and
    any dialog failure is swallowed — logging to disk is the guarantee.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        log_file = open(base_dir / "trakklicense.log", "a", encoding="utf-8")
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        pass

    err_path = error_log_path(base_dir)

    def _hook(exc_type, exc_value, tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, tb))[-4000:]
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            with open(err_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{stamp}] Unhandled exception:\n{text}\n")
        except Exception:
            pass
        # No dialog in headless/offscreen runs (tests, CI).
        if os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
            return
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is None:
                return
            QMessageBox.critical(
                None, "TRAKKLICENSE",
                "An unexpected error occurred.\n"
                f"Details were saved to:\n{err_path}")
        except Exception:
            pass

    sys.excepthook = _hook
    return err_path
