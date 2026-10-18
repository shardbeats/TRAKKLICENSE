"""IPI identifiers: optional {IF} blocks, profile autofill, checkbox gate, format hint."""
import os
from pathlib import Path

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

ROOT = Path(__file__).resolve().parents[1]


def _sample(**over):
    s = {
        "CONTRACT_DATE": "2026-09-09", "PRODUCT_TITLE": "B",
        "PRODUCER_ALIAS": "P", "PRODUCT_OWNER_FULLNAME": "O",
        "CUSTOMER_FULLNAME": "C", "CUSTOMER_ALIAS": "A",
        "CUSTOMER_ADDRESS": "X", "LICENSE_NAME": "L",
        "PRODUCT_PRICE": "300 MXN", "PRODUCT_PRICE_WORD": "three hundred MXN",
        "FILE_TYPE": "WAV + stems", "TERM_YEARS": "10",
        "TERM_START": "2026-09-09", "TERM_END": "2036-09-08",
        "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
        "ROYALTY_AMOUNT": "3%", "SAMPLES": "None declared",
        "STATE_PROVINCE_COUNTRY": "Y", "COUNTRY": "Y",
        "CREDIT_LINE": "Prod. by P", "FOLIO": "LIC-2026-0001",
        "DISTRIBUTE_COPIES": "unlimited", "DISTRIBUTE_COPIES_WORD": "unlimited",
        "AUDIO_STREAMS": "unlimited", "AUDIO_STREAMS_WORD": "unlimited",
    }
    s.update(over)
    return s


def test_ipi_blocks_render_only_when_filled():
    from app.engine.renderer import render
    for name in ("exclusive_10y.md", "non_exclusive_lease.md",
                 "exclusive_10y_ES.md", "non_exclusive_lease_ES.md"):
        tpl = (ROOT / "app" / "seed_templates" / name).read_text(encoding="utf-8")
        text, missing = render(tpl, _sample(PRODUCER_IPI="12345678901"))
        assert missing == set(), f"{name}: {missing}"
        assert "12345678901" in text
        assert "CUSTOMER_IPI" not in text and "{IF" not in text
        text2, missing2 = render(tpl, _sample(PRODUCER_IPI="", CUSTOMER_IPI=""))
        assert missing2 == set(), f"{name}: {missing2}"
        assert "IPI:" not in text2


def test_build_render_data_defaults_ipi_empty():
    from app.services.generation import build_render_data
    d = build_render_data({"PRODUCT_TITLE": "B"})
    assert d["PRODUCER_IPI"] == "" and d["CUSTOMER_IPI"] == ""


def test_ipi_persisted_in_sale(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    from app.database.seed import ensure_seed
    from app.database import repositories as repo
    from app.services.sale_service import save_current_sale
    db = tmp_path / "ipi.db"
    ensure_seed(db)
    preset = repo.list_presets(db)[0]
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "PRODUCER_IPI": "12345678901",
            "CUSTOMER_FULLNAME": "c", "CUSTOMER_ALIAS": "a", "CUSTOMER_IPI": "",
            "LICENSE_NAME": "L", "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "5", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    out = save_current_sale(form, preset, preset["id"], db=db)
    s = repo.get_sale(db, out["sale_id"])
    assert s["producer_ipi"] == "12345678901"
    assert s["customer_ipi"] == ""
    assert "12345678901" in s["rendered_text"]


def test_cover_appends_ipi_when_present():
    from app.services import document_service as docs
    base = {"out_dir": "", "filename_prefix": "TRAKKLICENSE", "filename_hash": True,
            "filename_folio": True, "footer_evidence": True, "footer_accepted": True,
            "pdf_cover": True}
    cov = docs.cover_data(base, {"PRODUCER_ALIAS": "P", "PRODUCT_OWNER_FULLNAME": "O",
                                 "CUSTOMER_ALIAS": "A", "CUSTOMER_FULLNAME": "C",
                                 "PRODUCER_IPI": "12345678901", "CUSTOMER_IPI": ""}, {})
    assert "12345678901" in cov["rows"][2][1]
    assert "IPI" not in cov["rows"][3][1]


@needs_qt
def test_profile_ipi_autofills_and_checks_box(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.services import settings as svc
    svc.save({"profile_producer_ipi": "12345678901"})
    assert svc.load()["profile_producer_ipi"] == "12345678901"
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w.generator.ipi_producer.text() == "12345678901"
        assert w.generator.ipi_check.isChecked()
        form, _kind = w.collect()
        assert form["PRODUCER_IPI"] == "12345678901"
        assert form["CUSTOMER_IPI"] == ""
        # opt out → both blank in render data
        w.generator.ipi_check.setChecked(False)
        form2, _ = w.collect()
        assert form2["PRODUCER_IPI"] == "" and form2["CUSTOMER_IPI"] == ""
        # opt in + customer IPI flows through
        w.generator.ipi_check.setChecked(True)
        w.generator.ipi_customer.setText("123456789")
        form3, _ = w.collect()
        assert form3["CUSTOMER_IPI"] == "123456789"
    finally:
        w.close()


@needs_qt
def test_malformed_ipi_warns_not_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.generator.ipi_check.setChecked(True)
        w.generator.ipi_producer.setText("ABC")
        w.on_generate()
        assert "PRODUCER_IPI" in w.generator.status.text()
        assert "ABC" in w._last_text  # renders as-is, never blocks preview
    finally:
        w.close()
