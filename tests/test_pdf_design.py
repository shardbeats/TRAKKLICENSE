"""PDF design: styled cover, headings, quotes, footers build for every template."""
from app.services.export import _inline_md, export_pdf
from app.services.generation import generate
from app.utils.paths import templates_dir


def test_inline_md_bold_and_escape():
    assert _inline_md("a **bold** move") == "a <b>bold</b> move"
    assert "&lt;b" in _inline_md("unclosed <b tag & co")


def _form():
    return {"CONTRACT_DATE": "2026-10-18", "PRODUCT_TITLE": "Beat <b> & Co",
            "PRODUCER_ALIAS": "P", "PRODUCT_OWNER_FULLNAME": "O",
            "CUSTOMER_FULLNAME": "C", "CUSTOMER_ALIAS": "A", "CUSTOMER_ADDRESS": "",
            "LICENSE_NAME": "L", "PRICE_AMOUNT": "49.99", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "MP3", "TERM_YEARS": "5", "TERM_START": "2026-10-18",
            "TERM_END": "2031-10-18", "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "0%", "SAMPLES": "None declared",
            "DISTRIBUTE_COPIES": "5000", "AUDIO_STREAMS": "500000",
            "FOLIO": "LIC-2026-0007"}


def test_all_templates_styled_pdf(tmp_path):
    preset = {"name": "L", "file_type": "MP3", "term_years": 5,
              "royalty": "0%", "publishing_shares": "s"}
    files = [p.name for p in templates_dir().glob("*.md")]
    assert len(files) >= 4
    for tf in files:
        res = generate(_form(), dict(preset, template_file=tf), "non-exclusive")
        assert res["missing"] == []
        for with_cover in (True, False):
            cover = {"title": f"{tf} — L",
                     "rows": [("Folio", "LIC-2026-0007"), ("Beat", "Beat <b> & Co"),
                              ("Price", res["data"]["PRODUCT_PRICE_WORD"]),
                              ("Empty", ""), ("SHA256", res["text_hash"])]} if with_cover else None
            p = export_pdf(res["text"], tmp_path, "Beat <b> & Co", "A", "2026-10-18",
                           "a1b2c3d4", "Evidence — foot", "TRAKKLICENSE",
                           "LETTER", "LIC-2026-0007", cover)
            assert p.stat().st_size > 2000  # styled doc (cover+footer) is never tiny
    a4 = export_pdf("# T\n> quote\n- item\n---\n**bold** & <raw>",
                    tmp_path, "B", "C", "d", "", "", "P", "A4", "", None)
    assert a4.stat().st_size > 1000
