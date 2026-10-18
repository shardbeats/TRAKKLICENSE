from app.services.generation import generate
from app.services.export import export_md, export_pdf


def test_generate_nonexclusive(tmp_path):
    form = {
        "CONTRACT_DATE": "2026-10-17",
        "PRODUCT_TITLE": "Demo Beat",
        "PRODUCER_ALIAS": "DemoProd",
        "PRODUCT_OWNER_FULLNAME": "Demo Owner",
        "CUSTOMER_FULLNAME": "Demo Customer",
        "CUSTOMER_ALIAS": "DemoArtist",
        "CUSTOMER_ADDRESS": "Demo City",
        "PRODUCT_PRICE": "49 USD",
        "FILE_TYPE": "WAV",
        "TERM_YEARS": "5",
        "TERM_START": "2026-10-17",
        "TERM_END": "2031-10-17",
        "STATE_PROVINCE_COUNTRY": "Texas, USA",
        "COUNTRY": "USA",
        "PUBLISHING_RIGHTS": "Producer retains 100%",
        "PUBLISHING_SHARES": "Producer 100%",
        "ROYALTY_AMOUNT": "0%",
        "SAMPLES": "None",
        "DISTRIBUTE_COPIES": "5000",
        "AUDIO_STREAMS": "500000",
    }
    preset = {"name": "WAV Lease", "file_type": "WAV", "term_years": 5, "royalty": "0%", "publishing_shares": "Producer 100%", "template_file": "non_exclusive_lease.md"}
    res = generate(form, preset, "non-exclusive")
    assert res["errors"] == []
    assert res["missing"] == []
    assert "Demo Beat" in res["text"]


def test_export_roundtrip(tmp_path):
    text = "# License\nHello Demo"
    md = export_md(text, tmp_path, "Demo Beat", "Artist", "2026-10-17")
    assert md.exists()
    pdf = export_pdf(text, tmp_path, "Demo Beat", "Artist", "2026-10-17")
    assert pdf.exists() and pdf.stat().st_size > 500
