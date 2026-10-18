"""Refactor v0.9: document_service + sale_service (extracted from MainWindow)."""
from app.services import document_service as docs
from app.services.sale_service import save_current_sale
from app.database.seed import ensure_seed
from app.database import repositories as repo


def _settings(**over):
    base = {"out_dir": "", "filename_prefix": "TRAKKLICENSE", "filename_hash": True,
            "filename_folio": True, "footer_evidence": True, "footer_accepted": True,
            "pdf_cover": True}
    base.update(over)
    return base


def test_evidence_footer_toggles():
    res = {"text_hash": "h" * 64, "template_file": "non_exclusive_lease.md", "template_version": "deadbeef"}
    assert "SHA256" in docs.evidence_footer(_settings(), res)
    assert docs.evidence_footer(_settings(footer_evidence=False), res) == ""
    assert "Accepted" not in docs.evidence_footer(_settings(footer_accepted=False), res)


def test_no_template_filename_leaks():
    """Internal template references must not reach client documents.

    The footer carries only the document hash: no filenames, no bare
    "Template v…" revision hash (that pin lives in the history record,
    where the template-changed warning uses it).
    """
    res = {"text_hash": "h" * 64, "template_file": "exclusive_10y.md",
           "template_version": "deadbeef"}
    footer = docs.evidence_footer(_settings(), res)
    assert "exclusive_10y.md" not in footer
    assert "deadbeef" not in footer
    assert "h" * 64 in footer  # document integrity hash kept
    cov = docs.cover_data(_settings(), {"LICENSE_NAME": "Exclusive License"}, res)
    assert cov["title"] == "Exclusive License"
    assert ".md" not in cov["title"]


def test_file_options_hash_and_folio():
    res = {"text_hash": "a" * 64}
    h8, prefix, folio = docs.file_options(_settings(), {"FOLIO": "LIC-2026-0001"}, res)
    assert h8 == "a" * 8 and prefix == "TRAKKLICENSE" and folio == "LIC-2026-0001"
    h8b, _, folio_draft = docs.file_options(_settings(), {"FOLIO": "DRAFT"}, res)
    assert folio_draft == "DRAFT"  # kept: preview filenames show DRAFT
    h8c, _, folio_off = docs.file_options(_settings(filename_folio=False), {"FOLIO": "LIC-2026-0001"}, res)
    assert folio_off == "" and h8c == "a" * 8
    h8d, _, _ = docs.file_options(_settings(filename_hash=False), {"FOLIO": ""}, res)
    assert h8d == ""


def test_cover_data_toggle(tmp_path):
    assert docs.cover_data(_settings(pdf_cover=False), {}, {}) is None
    cov = docs.cover_data(_settings(), {"PRODUCT_TITLE": "B", "FOLIO": "LIC-1"}, {"text_hash": "x"})
    assert cov["rows"][1] == ("Beat", "B")


def test_resolve_out_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    custom = tmp_path / "mine"
    assert docs.resolve_out_dir(_settings(out_dir=str(custom))) == custom
    assert custom.exists()
    default = docs.resolve_out_dir(_settings(out_dir=""))
    assert default.exists()


def test_save_current_sale_assigns_folio(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    db = tmp_path / "s.db"
    ensure_seed(db)
    preset = repo.list_presets(db)[0]
    form = {"CONTRACT_DATE": "2026-10-17", "PRODUCT_TITLE": "B", "PRODUCER_ALIAS": "P",
            "PRODUCT_OWNER_FULLNAME": "O", "CUSTOMER_FULLNAME": "C",
            "CUSTOMER_ALIAS": "A", "CUSTOMER_ADDRESS": "", "LICENSE_NAME": preset["name"],
            "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD", "FILE_TYPE": "MP3",
            "TERM_YEARS": "5", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None declared",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    out = save_current_sale(form, preset, preset["id"], db=db)
    assert out["folio"].startswith("LIC-")
    assert out["folio"] in out["res"]["text"]
    assert out["res"]["text_hash"] == repo.get_sale(db, out["sale_id"])["text_hash"]
