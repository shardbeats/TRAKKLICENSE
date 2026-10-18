"""Shell test: menubar only (no toolbars, no sidebars)."""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRAKKLICENSE_SKIP_GUI") == "1", reason="gui skip"
)

try:
    from PySide6.QtWidgets import QApplication, QToolBar, QTabWidget, QListWidget
    HAS_QT = True
except ImportError:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="PySide6 missing")


@needs_qt
def test_shell_menus_toolbar_and_views(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert [m.text() for m in w.menuBar().actions()] == ["&File", "&View", "&Help"]
        file_items = [a.text() for a in w.menuBar().actions()[0].menu().actions() if a.text()]
        assert file_items == ["Generate preview", "Export PDF",
                              "Save to history", "Settings…", "Exit"]
        # no toolbars, no sidebars, no tab bars — menubar only
        assert len(w.findChildren(QToolBar)) == 0
        assert len(w.findChildren(QTabWidget)) == 0
        assert not hasattr(w, "nav")
        # view shortcuts (tabs navigate via Ctrl+1..4)
        assert w.act_generate.shortcut().toString() == "F5"
        assert w._view_actions[0].shortcut().toString() == "Ctrl+1"
        # actions actually work (menu + contextual footer buttons share slots)
        w.act_generate.trigger()
        assert len(w._last_text) > 1000
        assert (w.btn_gen.text(),
                w.btn_pdf.text(), w.btn_save.text()) == (
            "Generate (F5)", "Export PDF", "Save")
        w.btn_gen.click()
        assert len(w._last_text) > 1000
        w._view_actions[2].trigger()
        assert w.tabs.currentIndex() == 2
        w._view_actions[0].trigger()
        assert w.tabs.currentIndex() == 0
    finally:
        w.close()
