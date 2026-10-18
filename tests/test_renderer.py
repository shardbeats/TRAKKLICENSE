from app.engine.renderer import render, find_variables


def test_both_syntaxes():
    tpl = "Hi {PRODUCER_ALIAS} / {{customer_alias}}!"
    text, missing = render(tpl, {"PRODUCER_ALIAS": "Shard", "CUSTOMER_ALIAS": "Kent"})
    assert text == "Hi Shard / Kent!"
    assert missing == set()


def test_alias_track_title():
    tpl = "Beat: {TRACK_TITLE}"
    text, missing = render(tpl, {"PRODUCT_TITLE": "Demo"})
    assert text == "Beat: Demo"
    assert missing == set()


def test_missing_reported():
    text, missing = render("Pay {PRODUCT_PRICE}", {})
    assert "{PRODUCT_PRICE}" in text
    assert "PRODUCT_PRICE" in missing


def test_if_block():
    tpl = "A{IF broadcast_rights} + radio{/ENDIF}B" if False else "A{IF BROADCAST_RIGHTS} + radio{ENDIF}B"
    text, _ = render(tpl, {"BROADCAST_RIGHTS": "No"})
    assert text == "AB"
    text2, _ = render(tpl, {"BROADCAST_RIGHTS": "Yes"})
    assert text2 == "A + radioB"


def test_find_variables():
    vars_ = find_variables("x {CONTRACT_DATE} y {{product_title}}")
    assert "CONTRACT_DATE" in vars_
    assert "PRODUCT_TITLE" in vars_
