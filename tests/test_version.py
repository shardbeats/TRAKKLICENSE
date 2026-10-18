"""Version single-source + frozen crash handling."""
import os
import re

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRAKKLICENSE_SKIP_GUI") == "1", reason="gui skip"
)

try:
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="PySide6 missing")


def test_version_single_source():
    """app/version.py is X.Y.Z; pyproject + builders parse the same file."""
    from pathlib import Path
    from app.version import __version__
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__
    root = Path(__file__).resolve().parents[1]
    assert 'app.version.__version__' in (root / "pyproject.toml").read_text(encoding="utf-8")
    src = (root / "build_exe.py").read_text(encoding="utf-8")
    assert "app" in src and "version.py" in src
    assert not (root / "build_installer.py").exists()
    assert not (root / "installer").exists()


def test_crash_handler_logs_without_dialog(tmp_path, monkeypatch):
    """Unhandled exceptions land in error.log; no dialog offscreen."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.utils.crash import install_crash_handler
    err = install_crash_handler(tmp_path)
    try:
        raise ValueError("boom-test")
    except ValueError:
        import sys
        sys.excepthook(*sys.exc_info())
    text = err.read_text(encoding="utf-8")
    assert "boom-test" in text and "ValueError" in text


@needs_qt
def test_window_title_and_about(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    from app.version import __version__
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert __version__ in w.windowTitle()
        helps = [a.text() for a in w.menuBar().actions()[2].menu().actions() if a.text()]
        assert helps == ["About TRAKKLICENSE…", "Legal disclaimer…"]
    finally:
        w.close()
