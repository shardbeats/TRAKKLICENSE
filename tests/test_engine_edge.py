import pytest
from app.engine.money_words import number_to_words
from app.engine.validators import validate
from app.engine.renderer import find_variables, render


def test_words_range():
    with pytest.raises(ValueError):
        number_to_words(10_000_00)


def test_validate_nonexclusive_minimal():
    ok = {
        "CONTRACT_DATE": "d", "PRODUCT_TITLE": "b", "PRODUCER_ALIAS": "p",
        "PRODUCT_OWNER_FULLNAME": "o", "CUSTOMER_FULLNAME": "c",
        "LICENSE_NAME": "L", "PRODUCT_PRICE": "1 USD",
    }
    assert validate(ok, "non-exclusive") == []


def test_find_vars_resolves_alias():
    assert "PRODUCT_TITLE" in find_variables("{TRACK_TITLE} + {{product_title}}")


def test_render_keeps_unknown():
    t, missing = render("a {NOPE_XYZ} b", {})
    assert "{NOPE_XYZ}" in t and "NOPE_XYZ" in missing
