from pathlib import Path
from app.database.seed import ensure_seed
from app.database.repositories import list_presets, save_sale, list_sales


def test_seed_and_sales(tmp_path):
    db = tmp_path / "t.db"
    ensure_seed(db)
    presets = list_presets(db)
    assert len(presets) == 5
    names = {p["name"] for p in presets}
    assert "Exclusive" in names and "Exclusive 10Y" not in names
    assert {p["term_years"] for p in presets} == {10}
    by_name = {p["name"]: p for p in presets}
    assert by_name["Exclusive"]["file_type"] == "WAV + stems"
    # re-seed never duplicates
    ensure_seed(db)
    assert len(list_presets(db)) == 5

    sid = save_sale(db, {
        "preset_id": presets[0]["id"],
        "contract_date": "2026-10-17",
        "beat_title": "Demo",
        "producer_alias": "Prod",
        "owner_fullname": "Owner",
        "customer_fullname": "Cust",
        "customer_alias": "Artist",
        "customer_address": "",
        "price": "29 USD",
        "price_words": "twenty-nine USD",
        "file_type": "MP3",
        "term_start": "2026-10-17",
        "term_end": "2031-10-17",
        "term_years": "5",
        "publishing_rights": "",
        "publishing_shares": "",
        "royalty": "0%",
        "samples": "None",
        "state_country": "",
        "country": "",
        "credit": "",
        "rendered_text": "hello",
    })
    assert sid == 1
    assert len(list_sales(db)) == 1
