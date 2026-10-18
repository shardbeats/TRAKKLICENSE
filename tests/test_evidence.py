import sqlite3
from pathlib import Path
from app.services.generation import compose_samples, sha256_text, template_version, generate
from app.services.export import export_md, export_pdf
from app.database.seed import ensure_seed
from app.database import repositories as repo


def test_compose_samples():
    assert compose_samples([], False) == "None declared"
    assert compose_samples([("", "")], True).startswith("None declared")
    s = compose_samples([("Loop A", "Splice"), ("Vox", "")], True)
    assert "1. Loop A" in s and "Source: Splice" in s and "2. Vox" in s


def test_hash_and_version():
    h = sha256_text("hello")
    assert len(h) == 64
    assert len(template_version("non_exclusive_lease.md")) == 8
    assert len(template_version("exclusive_10y.md")) == 8


def test_export_filenames_with_hash(tmp_path):
    md = export_md("# T", tmp_path, "Beat!", "Art", "2026-10-17", "abc123xy", "foot")
    assert "abc123xy" in md.name and md.suffix == ".md"
    assert "Evidence" not in md.read_text() or "foot" in md.read_text()
    pdf = export_pdf("# T\nhello", tmp_path, "Beat!", "Art", "2026-10-17", "abc123xy", "foot")
    assert "abc123xy" in pdf.name and pdf.stat().st_size > 500


def test_sales_evidence_columns(tmp_path):
    db = tmp_path / "e.db"
    ensure_seed(db)
    con = sqlite3.connect(str(db))
    cols = {r[1] for r in con.execute("PRAGMA table_info(sales)").fetchall()}
    con.close()
    assert {"accepted_at", "template_version", "text_hash"} <= cols
    presets = repo.list_presets(db)
    sid = repo.save_sale(db, {"preset_id": presets[0]["id"], "contract_date": "d",
        "beat_title": "b", "producer_alias": "p", "owner_fullname": "o",
        "customer_fullname": "c", "customer_alias": "a", "customer_address": "",
        "price": "1 USD", "price_words": "one USD", "file_type": "MP3",
        "term_start": "", "term_end": "", "term_years": "",
        "publishing_rights": "", "publishing_shares": "", "royalty": "",
        "samples": compose_samples([("L", "S")], True),
        "state_country": "", "country": "", "credit": "",
        "rendered_text": "txt", "accepted_at": "2026-10-17T10:00:00",
        "template_version": "deadbeef", "text_hash": "h" * 64})
    s = repo.get_sale(db, sid)
    assert s["text_hash"] == "h" * 64 and s["template_version"] == "deadbeef"


def test_es_templates_render():
    from app.utils.paths import templates_dir
    for f in ("non_exclusive_lease_ES.md", "exclusive_10y_ES.md"):
        assert (templates_dir() / f).exists()
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "CUSTOMER_ADDRESS": "", "LICENSE_NAME": "L",
            "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "5", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None declared",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1"}
    res = generate(form, {"name": "L", "template_file": "non_exclusive_lease_ES.md",
                          "file_type": "MP3", "term_years": 5,
                          "royalty": "0%", "publishing_shares": "x"}, "non-exclusive")
    assert "CONTRATO" in res["text"] and res["missing"] == []
