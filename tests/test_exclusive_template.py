from pathlib import Path
from app.engine.renderer import render
from app.engine.validators import validate

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = {
    "CONTRACT_DATE": "September 9, 2026",
    "PRODUCT_TITLE": "Demo Beat",
    "PRODUCER_ALIAS": "Demo Producer",
    "PRODUCT_OWNER_FULLNAME": "Demo Owner Fullname",
    "CUSTOMER_FULLNAME": "Demo Customer Fullname",
    "CUSTOMER_ALIAS": "Demo Artist",
    "CUSTOMER_ADDRESS": "Demo City",
    "LICENSE_NAME": "Exclusive 10Y",
    "PRODUCT_PRICE": "$300 MXN",
    "PRODUCT_PRICE_WORD": "three hundred MXN",
    "FILE_TYPE": "WAV + stems",
    "TERM_YEARS": "10",
    "TERM_START": "September 9, 2026",
    "TERM_END": "September 8, 2036",
    "PUBLISHING_RIGHTS": "50/50 split.",
    "PUBLISHING_SHARES": "Licensor 50% / Licensee 50%",
    "ROYALTY_AMOUNT": "3%",
    "SAMPLES": "None declared",
    "STATE_PROVINCE_COUNTRY": "Austin, USA",
    "COUNTRY": "USA",
    "CREDIT_LINE": "Prod. by Demo Producer",
    "FOLIO": "LIC-2026-0001",
}

# Synthetic stand-ins (never real personal data): the no-leak mechanism is
# what's pinned here, not anyone's identity. Nothing in this repo may contain
# these strings outside FORBIDDEN lists.
FORBIDDEN = [
    "Juan Perez Garcia", "Estudio Demo Records", "Demo Producer Alias",
    "00012345678", "Ciudad Ficticia", "MC Prueba",
    "Lopez", "Hernandez Demo",
    "Beat De Ejemplo",
]


def test_exclusive_template_renders_clean():
    tpl = (ROOT / "app" / "seed_templates" / "exclusive_10y.md").read_text(encoding="utf-8")
    text, missing = render(tpl, SAMPLE)
    assert missing == set(), f"missing: {missing}"
    assert "{" not in text.replace("{{", "").replace("}}", "") or "{PRODUCT" not in text
    # no unreplaced vars
    assert "{CONTRACT_DATE}" not in text
    assert "{PRODUCT_TITLE}" not in text


def test_no_personal_data_in_template_source():
    src = (ROOT / "app" / "seed_templates" / "exclusive_10y.md").read_text(encoding="utf-8")
    for s in FORBIDDEN:
        assert s.lower() not in src.lower(), f"leak: {s}"


def test_no_personal_data_in_render():
    tpl = (ROOT / "app" / "seed_templates" / "exclusive_10y.md").read_text(encoding="utf-8")
    text, _ = render(tpl, SAMPLE)
    for s in FORBIDDEN:
        assert s.lower() not in text.lower(), f"leak in render: {s}"


def test_exclusive_validators():
    assert validate(SAMPLE, "exclusive") == []
    bad = dict(SAMPLE)
    del bad["TERM_YEARS"]
    assert "TERM_YEARS" in validate(bad, "exclusive")
