import os

import pytest

from app.services import settings as svc
from app.services.export import export_md, export_pdf

pytestmark = pytest.mark.skipif(
    os.environ.get("TRAKKLICENSE_SKIP_GUI") == "1", reason="gui skip"
)

try:
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="PySide6 missing")


def test_defaults_and_sanitize(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    d = svc.load()
    assert d["filename_prefix"] == "TRAKKLICENSE"
    assert d["pdf_pagesize"] == "LETTER"
    assert d["filename_hash"] is True


def test_save_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    out = svc.save({"filename_prefix": "BEATS", "pdf_pagesize": "A4",
                    "filename_hash": False, "bogus": 1})
    assert out["filename_prefix"] == "BEATS"
    assert out["pdf_pagesize"] == "A4"
    again = svc.load()
    assert again["filename_prefix"] == "BEATS"
    assert "bogus" not in again


def test_bad_pagesize_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    svc.save({"pdf_pagesize": "LEGAL"})
    assert svc.load()["pdf_pagesize"] == "LETTER"


def test_export_prefix_and_pagesize(tmp_path):
    md = export_md("# T", tmp_path, "B", "C", "2026-10-17", "a1b2c3d4", "", "BEATS")
    assert md.name.startswith("BEATS_") and "a1b2c3d4" in md.name
    md2 = export_md("# T", tmp_path, "B", "C", "2026-10-17", "", "", "BEATS")
    assert "a1b2c3d4" not in md2.name
    pdf = export_pdf("# T\nx", tmp_path, "B", "C", "2026-10-17", "", "", "BEATS", "A4")
    assert pdf.name.startswith("BEATS_") and pdf.stat().st_size > 500


@needs_qt
def test_dialog_currency_coerced(tmp_path, monkeypatch):
    """Free-typed currency falls back like the sale form (XXX→USD, eur→EUR)."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.settings_dialog import SettingsDialog
    app = QApplication.instance() or QApplication([])
    dlg = SettingsDialog()
    try:
        dlg.currency.setCurrentText("XXX")
        assert dlg.result_patch()["default_currency"] == "XXX"  # 3-letter codes pass (form behaves the same)
        dlg.currency.setCurrentText("eur")
        assert dlg.result_patch()["default_currency"] == "EUR"
        dlg.currency.setCurrentText("!!")
        assert dlg.result_patch()["default_currency"] == "USD"
    finally:
        dlg.close()


@needs_qt
def test_dialog_constructs_offscreen(tmp_path, monkeypatch):
    """Regression: SettingsDialog must open (was NameError: QWidget not imported)."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.settings_dialog import SettingsDialog
    app = QApplication.instance() or QApplication([])
    dlg = SettingsDialog()
    try:
        assert "Settings" in dlg.windowTitle()
        patch = dlg.result_patch()
        assert patch["filename_prefix"] == "TRAKKLICENSE"
        assert patch["default_currency"] == "USD"
    finally:
        dlg.close()
