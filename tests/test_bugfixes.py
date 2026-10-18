"""Bug-hunt regressions (2026-10-18): export cover escaping, preset FK delete,
stale export flush, money cents, samples guard, folio-off saves."""
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


def test_pdf_cover_title_with_markup_chars(tmp_path):
    from app.services.export import export_pdf
    p = export_pdf("# T\nbody", tmp_path, "B", "C", "d", "", "",
                   "P", "LETTER", "", {"title": "unclosed <b tag & Mireia", "rows": []})
    assert p.stat().st_size > 500


def test_money_keeps_cents():
    from app.engine.money_words import money_to_words
    assert money_to_words(300, "en", "MXN") == "three hundred MXN"
    assert money_to_words(49.99, "en", "USD") == "forty-nine and 99/100 USD"
    assert money_to_words(10.5, "en", "USD") == "ten and 50/100 USD"


def test_price_cents_flow_into_render():
    from app.services.generation import build_render_data
    d = build_render_data({"PRICE_AMOUNT": "49.99", "PRICE_CURRENCY": "USD"})
    assert d["PRODUCT_PRICE_WORD"] == "forty-nine and 99/100 USD"


def test_samples_checked_but_empty_flagged():
    from app.services.generation import generate
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "LICENSE_NAME": "L",
            "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "5", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%",
            "SAMPLES": "None declared — box checked but no items listed",
            "SAMPLES_CONFIRMED": "1",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    res = generate(form, {"name": "L", "template_file": "non_exclusive_lease.md",
                          "file_type": "MP3", "term_years": 5,
                          "royalty": "0%", "publishing_shares": "x"}, "non-exclusive")
    assert "SAMPLES" in res["errors"]


def test_delete_preset_used_by_sale_returns_false(tmp_path):
    from app.database.seed import ensure_seed
    from app.database import repositories as repo
    db = tmp_path / "fk.db"
    ensure_seed(db)
    used = repo.list_presets(db)[0]
    repo.save_sale(db, {"preset_id": used["id"], "contract_date": "d",
        "beat_title": "b", "producer_alias": "p", "owner_fullname": "o",
        "customer_fullname": "c", "customer_alias": "a", "customer_address": "",
        "price": "1 USD", "price_words": "one", "file_type": "MP3",
        "term_start": "", "term_end": "", "term_years": "",
        "publishing_rights": "", "publishing_shares": "", "royalty": "",
        "samples": "None", "state_country": "", "country": "", "credit": "",
        "rendered_text": "t", "accepted_at": "", "template_version": "",
        "text_hash": "", "folio": "", "template_file": ""})
    assert repo.delete_preset(db, used["id"]) is False
    assert repo.get_preset(db, used["id"]) is not None  # still there
    fresh = repo.create_preset(db, {"name": "Temp", "kind": "non-exclusive",
        "term_years": 5, "file_type": "MP3", "royalty": "0%",
        "publishing_shares": "x", "template_file": "non_exclusive_lease.md"})
    assert repo.delete_preset(db, fresh) is True


def test_folio_disabled_saves_empty_not_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    from app.services import settings as svc
    from app.services.sale_service import save_current_sale
    from app.database.seed import ensure_seed
    from app.database import repositories as repo
    svc.save({"folio_enabled": False})
    db = tmp_path / "nf.db"
    ensure_seed(db)
    preset = repo.list_presets(db)[0]
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "LICENSE_NAME": preset["name"],
            "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "5", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    out = save_current_sale(form, preset, preset["id"], db=db)
    assert out["folio"] == ""
    assert out["res"]["data"]["FOLIO"] == ""
    assert "DRAFT" not in out["res"]["text"]


@needs_qt
def test_price_warning_does_not_block(tmp_path, monkeypatch):
    """Non-numeric/negative amounts warn in status; preview still renders."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.price_amount.setText("abc")
        w.on_generate()
        assert "greater than zero" in w.status.text()
        assert len(w._last_text) > 1000
        w.price_amount.setText("-5")
        w.on_generate()
        assert "greater than zero" in w.status.text()
        w.price_amount.setText("500")
        w.on_generate()
        assert "greater than zero" not in w.status.text()
    finally:
        w.close()


@needs_qt
def test_profile_location_never_fills_buyer_address(tmp_path, monkeypatch):
    """Legacy profile_location must not print the producer's city as buyer domicile."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.services import settings as svc
    svc.save({"profile_location": "Ciudad Demo"})
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w.inputs["CUSTOMER_ADDRESS"].text() == ""
        w.on_generate()
        assert "Ciudad Demo" not in w._last_text
    finally:
        w.close()


@needs_qt
def test_history_delete_button(tmp_path, monkeypatch):
    """Delete selected removes the record (with confirmation); folio counter not reused."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QMessageBox
    from app.services import settings as svc
    svc.save({"open_after_export": False, "require_acceptance": False,
              "out_dir": str(tmp_path / "out")})
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    from app.ui.main_window import MainWindow
    from app.database.repositories import list_sales
    from app.utils.paths import db_path
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.on_save()
        w.on_save()
        assert len(list_sales(db_path())) == 2
        assert w.history.btn_delete.text() == "Delete selected"
        w.history.list.setCurrentRow(0)
        w.history.delete_selected()
        remaining = list_sales(db_path())
        assert len(remaining) == 1
        # folio sequence keeps going (sale #3 gets ...-0003, never reuses ...-0001)
        w.on_save()
        folios = [s["folio"] for s in list_sales(db_path())]
        assert any(f.endswith("-0003") for f in folios)
    finally:
        w.close()


@needs_qt
def test_export_auto_saves_with_real_folio(tmp_path, monkeypatch):
    """Exporting must auto-save: no DRAFT in file, folio in history."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.services import settings as svc
    svc.save({"open_after_export": False, "require_acceptance": False,
              "out_dir": str(tmp_path / "out")})
    from app.ui.main_window import MainWindow
    from app.database.repositories import list_sales
    from app.utils.paths import db_path
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert list_sales(db_path()) == []
        w.inputs["PRODUCT_TITLE"].setText("FolioBeat")
        w.inputs["CUSTOMER_ALIAS"].setText("MC Auto")
        w.on_export_pdf()
        sales = list_sales(db_path())
        assert len(sales) == 1
        assert sales[0]["folio"].startswith("LIC-")
        assert "DRAFT" not in w._last_text
        assert sales[0]["folio"] in w._last_text
        assert sales[0]["folio"] in w.status.text()
        w.on_export_pdf()
        assert len(list_sales(db_path())) == 2
        assert "DRAFT" not in w._last_text
    finally:
        w.close()


@needs_qt
def test_export_uses_fresh_text_not_stale(tmp_path, monkeypatch):
    """Filename AND content must match current inputs (flush pending preview)."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.services import settings as svc
    svc.save({"open_after_export": False, "require_acceptance": False,
              "out_dir": str(tmp_path / "out")})
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.inputs["PRODUCT_TITLE"].setText("CambioReciente")
        assert w._preview_timer.isActive()  # debounce pending → would be stale
        w.on_export_pdf()
        assert "CambioReciente" in w._last_text
        assert "CambioReciente" in w.status.text()
    finally:
        w.close()


def test_license_name_hides_tier_name():
    """Contracts show the legal term (Exclusive/Non-Exclusive License),
    never the commercial tier name (WAV Lease, Exclusive 10Y)."""
    from app.services.generation import build_render_data, generate, license_display_name
    assert license_display_name("exclusive") == "Exclusive License"
    assert license_display_name("NON-EXCLUSIVE") == "Non-Exclusive License"
    assert license_display_name("weird") == "Non-Exclusive License"
    excl = {"name": "Exclusive 10Y", "kind": "exclusive", "term_years": 10,
            "file_type": "WAV", "royalty": "3%", "publishing_shares": "50/50"}
    wav = {"name": "WAV Lease", "kind": "non-exclusive", "term_years": 5,
           "file_type": "WAV", "royalty": "0%", "publishing_shares": "keep"}
    assert build_render_data({}, excl)["LICENSE_NAME"] == "Exclusive License"
    assert build_render_data({}, wav)["LICENSE_NAME"] == "Non-Exclusive License"
    # explicit values respected
    assert build_render_data({"LICENSE_NAME": "Custom"}, wav)["LICENSE_NAME"] == "Custom"
    res = generate({"PRODUCT_TITLE": "B"}, excl, "exclusive")
    assert "Exclusive 10Y" not in res["text"]
    assert "Exclusive License" in res["text"]
    res_es = generate({"PRODUCT_TITLE": "B"},
                      dict(excl, template_file="exclusive_10y_ES.md"), "exclusive")
    assert "Licencia Exclusiva" in res_es["text"]
    assert "Exclusive 10Y" not in res_es["text"]


@needs_qt
def test_gui_pdf_has_no_tier_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        # commercial tier names must not leak; "Exclusive" alone is a substring
        # of the legal term, so check a distinctive one (WAV Lease).
        idx = next(i for i in range(w.preset_cb.count())
                   if w.preset_cb.itemText(i).startswith("WAV Lease"))
        w.preset_cb.setCurrentIndex(idx)
        w.on_generate()
        assert "WAV Lease" not in w._last_text
        assert w._last_data["LICENSE_NAME"] == "Non-Exclusive License"
        assert w.inputs["TERM_YEARS"].text() == "10"
    finally:
        w.close()


def test_governing_manual_fields_no_presets():
    """No governing quick-picks: manual state/country validate exclusive OK,
    and the combo is gone from the UI."""
    from app.services.generation import generate, build_render_data
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "LICENSE_NAME": "L",
            "PRICE_AMOUNT": "500", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "WAV", "TERM_YEARS": "10", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "Texas, USA", "COUNTRY": "USA",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "3%", "SAMPLES": "None",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    res = generate(form, {"name": "Exclusive", "kind": "exclusive",
                          "template_file": "exclusive_10y.md"}, "exclusive")
    assert res["errors"] == []
    assert "Texas, USA" in res["text"]
    # COUNTRY derived from "State, Country" when blank; explicit respected
    assert build_render_data({"STATE_PROVINCE_COUNTRY": "Texas, USA"})["COUNTRY"] == "USA"
    assert build_render_data({"STATE_PROVINCE_COUNTRY": "Guadalajara, Mexico"})["COUNTRY"] == "Mexico"
    assert build_render_data({"STATE_PROVINCE_COUNTRY": "USA"})["COUNTRY"] == "USA"
    assert build_render_data({"STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y"})["COUNTRY"] == "Y"


@needs_qt
def test_governing_combo_removed(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert not hasattr(w.generator, "gov_cb")
        assert "COUNTRY" not in w.inputs
        assert w.inputs["STATE_PROVINCE_COUNTRY"].placeholderText() == "e.g. Texas, USA"
    finally:
        w.close()
