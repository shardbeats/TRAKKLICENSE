import datetime
from app.services import settings as svc
from app.services.export import export_pdf


def test_folio_sequence_and_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    y = datetime.date.today().year
    assert svc.next_folio() == f"LIC-{y}-0001"
    assert svc.next_folio() == f"LIC-{y}-0002"
    # previous year rolls over
    svc.save({"folio_year": y - 1, "folio_seq": 99})
    assert svc.next_folio() == f"LIC-{y}-0001"
    # disabled
    svc.save({"folio_enabled": False})
    assert svc.next_folio() == ""


def test_folio_in_text_and_filename(tmp_path):
    from app.services.generation import generate
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "LICENSE_NAME": "L",
            "PRICE_AMOUNT": "10", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "1", "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None",
            "DISTRIBUTE_COPIES": "1", "AUDIO_STREAMS": "1",
            "FOLIO": "LIC-2026-0042"}
    res = generate(form, {"name": "L", "template_file": "non_exclusive_lease.md",
                          "file_type": "MP3", "term_years": 1,
                          "royalty": "0%", "publishing_shares": "x"}, "non-exclusive")
    assert "LIC-2026-0042" in res["text"]
    p = export_pdf(res["text"], tmp_path, "b", "a", "d", "hash1234", "",
                   "TRAKKLICENSE", "LETTER", "LIC-2026-0042",
                   {"title": "T", "rows": [("Folio", "LIC-2026-0042")]})
    assert "LIC-2026-0042" in p.name and p.stat().st_size > 500


def test_profile_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    svc.save({"profile_alias": "DemoProd", "profile_state_country": "Texas, USA"})
    d = svc.load()
    assert d["profile_alias"] == "DemoProd"
