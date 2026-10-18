"""Document brand: setting → producer alias → default; cover/footers use it."""
import os

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


def test_brand_resolution_chain():
    from app.services.document_service import brand_name
    assert brand_name({"brand_name": "Shard Beats", "profile_alias": "X"}) == "Shard Beats"
    assert brand_name({"brand_name": "", "profile_alias": "Test Alias"}) == "Test Alias"
    assert brand_name({"brand_name": "  ", "profile_alias": ""}) == "TRAKKLICENSE"
    assert brand_name({}) == "TRAKKLICENSE"


def test_brand_prefers_sale_form_alias():
    """The licensor named in this contract governs the brand on its PDF."""
    from app.services.document_service import brand_name
    s = {"brand_name": "", "profile_alias": "Profile Alias"}
    assert brand_name(s, "Sale Alias") == "Sale Alias"
    assert brand_name(s, "") == "Profile Alias"
    assert brand_name(s, "  ") == "Profile Alias"
    assert brand_name({"brand_name": "Explicit", "profile_alias": "P"}, "Sale") == "Explicit"
    assert brand_name({}, "Sale Alias") == "Sale Alias"


def test_brand_setting_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    from app.services import settings as svc
    assert svc.load()["brand_name"] == ""
    svc.save({"brand_name": "Shard Beats"})
    assert svc.load()["brand_name"] == "Shard Beats"


def test_cover_uses_brand(tmp_path):
    from app.services.export import _cover_story, _styles
    story = _cover_story({"title": "T", "rows": []}, _styles(), "Shard Beats")
    texts = [getattr(el, "text", "") for el in story]
    assert any("Shard Beats" in t for t in texts)
    assert not any("TRAKKLICENSE" in t for t in texts)
    story2 = _cover_story({"title": "T", "rows": []}, _styles(), "TRAKKLICENSE")
    assert any("TRAKKLICENSE" in t for t in [getattr(el, "text", "") for el in story2])


def test_export_pdf_brand_default_preserved(tmp_path):
    from app.services.export import export_pdf
    p = export_pdf("# T\nhello", tmp_path, "B", "C", "d")
    assert p.stat().st_size > 500
    p2 = export_pdf("# T\nhello", tmp_path, "B2", "C", "d", brand="Shard Beats")
    assert p2.stat().st_size > 500


@needs_qt
def test_export_uses_profile_alias_as_brand(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from pathlib import Path
    from app.services import settings as svc
    svc.save({"open_after_export": False, "require_acceptance": False,
              "out_dir": str(tmp_path / "out"),
              "profile_alias": "Test Alias", "brand_name": ""})
    import app.ui.main_window as mw
    from app.ui.main_window import MainWindow
    seen = {}
    real_export = mw.export_pdf

    def _capture(*a, **k):
        seen.update(k)
        return real_export(*a, **k)

    monkeypatch.setattr(mw, "export_pdf", _capture)
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.on_export_pdf()
        assert seen.get("brand") == "Test Alias"
        assert (tmp_path / "out").glob("*.pdf")
    finally:
        w.close()


@needs_qt
def test_explicit_brand_wins_over_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.services import settings as svc
    svc.save({"open_after_export": False, "require_acceptance": False,
              "out_dir": str(tmp_path / "out"),
              "profile_alias": "Test Alias", "brand_name": "Shard Beats"})
    import app.ui.main_window as mw
    from app.ui.main_window import MainWindow
    seen = {}
    real_export = mw.export_pdf

    def _capture(*a, **k):
        seen.update(k)
        return real_export(*a, **k)

    monkeypatch.setattr(mw, "export_pdf", _capture)
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.on_export_pdf()
        assert seen.get("brand") == "Shard Beats"
    finally:
        w.close()
