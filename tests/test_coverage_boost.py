from pathlib import Path
from app.database.seed import ensure_seed
from app.database import repositories as repo
from app.services.generation import build_render_data, generate
from app.utils import paths as p


def test_preset_crud(tmp_path):
    db = tmp_path / "c.db"
    ensure_seed(db)
    nid = repo.create_preset(db, {"name": "T", "kind": "non-exclusive",
                                  "term_years": 1, "file_type": "MP3",
                                  "royalty": "0%", "publishing_shares": "P100",
                                  "template_file": "non_exclusive_lease.md"})
    assert repo.get_preset(db, nid)["name"] == "T"
    assert repo.update_preset(db, nid, {"file_type": "WAV", "nope": 1})
    assert repo.get_preset(db, nid)["file_type"] == "WAV"
    assert not repo.update_preset(db, nid, {"nope": 1})
    assert repo.delete_preset(db, nid)
    assert repo.get_preset(db, nid) is None
    assert not repo.delete_preset(db, 999999)


def test_sale_get(tmp_path):
    db = tmp_path / "s.db"
    ensure_seed(db)
    presets = repo.list_presets(db)
    sid = repo.save_sale(db, {"preset_id": presets[0]["id"], "contract_date": "d",
        "beat_title": "b", "producer_alias": "p", "owner_fullname": "o",
        "customer_fullname": "c", "customer_alias": "a", "customer_address": "",
        "price": "1", "price_words": "one", "file_type": "MP3",
        "term_start": "", "term_end": "", "term_years": "",
        "publishing_rights": "", "publishing_shares": "", "royalty": "",
        "samples": "", "state_country": "", "country": "", "credit": "",
        "rendered_text": "txt"})
    assert repo.get_sale(db, sid)["beat_title"] == "b"
    assert repo.get_sale(db, 999999) is None


def test_build_data_autofill():
    d = build_render_data({"PRICE_AMOUNT": "2500", "PRICE_CURRENCY": "USD",
                           "DISTRIBUTE_COPIES": "2500",
                           "PRODUCER_ALIAS": "P"}, None)
    assert d["PRODUCT_PRICE"] == "2500 USD"
    assert "two thousand five hundred" in d["DISTRIBUTE_COPIES_WORD"]
    assert "USD" in d["PRODUCT_PRICE_WORD"]
    assert d["CREDIT_LINE"] == "Prod. by P"


def test_build_data_price_direct():
    d = build_render_data({"PRODUCT_PRICE": "2500 USD", "PRODUCER_ALIAS": "P"}, None)
    assert "USD" in d["PRODUCT_PRICE_WORD"]


def test_generate_missing_template_fallback():
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "LICENSE_NAME": "L", "PRODUCT_PRICE": "1 USD"}
    res = generate(form, {"name": "L", "template_file": "nope_missing.md",
                          "file_type": "MP3", "term_years": 1,
                          "royalty": "0%", "publishing_shares": "x"},
                   "non-exclusive")
    assert "NON-EXCLUSIVE" in res["text"]


def test_paths_helpers(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path / "d"))
    assert p.base_dir() == tmp_path / "d"
    assert p.db_path().parent == tmp_path / "d"
    assert p.out_dir().exists()
    assert p.templates_dir().exists()
