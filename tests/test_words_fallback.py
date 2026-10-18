from app.services.generation import build_render_data, generate


def test_unlimited_copies_pass_through():
    d = build_render_data({"DISTRIBUTE_COPIES": "unlimited",
                           "AUDIO_STREAMS": "unlimited",
                           "PRODUCT_PRICE": "10 USD",
                           "PRODUCER_ALIAS": "P"}, None)
    assert d["DISTRIBUTE_COPIES_WORD"] == "unlimited"
    assert d["AUDIO_STREAMS_WORD"] == "unlimited"


def test_unlimited_renders_no_placeholders():
    form = {"CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
            "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
            "CUSTOMER_ALIAS": "a", "CUSTOMER_ADDRESS": "",
            "PRICE_AMOUNT": "500", "PRICE_CURRENCY": "USD",
            "FILE_TYPE": "WAV + stems", "TERM_YEARS": "10",
            "TERM_START": "a", "TERM_END": "b",
            "STATE_PROVINCE_COUNTRY": "X", "COUNTRY": "Y",
            "PUBLISHING_RIGHTS": "r", "PUBLISHING_SHARES": "s",
            "ROYALTY_AMOUNT": "3%", "SAMPLES": "None declared",
            "DISTRIBUTE_COPIES": "unlimited", "AUDIO_STREAMS": "unlimited"}
    res = generate(form, {"name": "Unlimited Lease", "template_file": "non_exclusive_lease.md",
                          "file_type": "WAV + stems", "term_years": 10,
                          "royalty": "3%", "publishing_shares": "s"}, "non-exclusive")
    assert res["missing"] == []
    assert "DISTRIBUTE_COPIES_WORD" not in res["text"]
