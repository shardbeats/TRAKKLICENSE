"""Gherkin steps (pytest-bdd) — business language for TRAKKLICENSE."""
import tempfile
from pathlib import Path

import pytest
from pytest_bdd import given, when, then, scenarios

from app.database.seed import ensure_seed
from app.database import repositories as repo
from app.services.generation import generate

scenarios("../features/license_generation.feature", "../features/presets.feature")

FORBIDDEN = ["juan perez garcia", "estudio demo records",
             "00012345678", "ciudad ficticia", "beat de ejemplo"]


def _base_form(**over):
    f = {
        "CONTRACT_DATE": "2026-10-17",
        "PRODUCT_TITLE": "Demo Beat",
        "PRODUCER_ALIAS": "DemoProd",
        "PRODUCT_OWNER_FULLNAME": "Demo Owner",
        "CUSTOMER_FULLNAME": "Demo Customer",
        "CUSTOMER_ALIAS": "Demo Artist",
        "CUSTOMER_ADDRESS": "Demo City",
        "PRICE_AMOUNT": "49",
        "PRICE_CURRENCY": "USD",
        "FILE_TYPE": "WAV",
        "TERM_YEARS": "5",
        "TERM_START": "2026-10-17",
        "TERM_END": "2031-10-17",
        "STATE_PROVINCE_COUNTRY": "Texas, USA",
        "COUNTRY": "USA",
        "PUBLISHING_RIGHTS": "Producer retains 100%",
        "PUBLISHING_SHARES": "Producer 100%",
        "ROYALTY_AMOUNT": "0%",
        "SAMPLES": "None declared",
        "DISTRIBUTE_COPIES": "5000",
        "AUDIO_STREAMS": "500000",
    }
    f.update(over)
    return f


@pytest.fixture
def ctx():
    tmp = tempfile.TemporaryDirectory()
    db = Path(tmp.name) / "t.db"
    ensure_seed(db)
    state = {"tmp": tmp, "db": db, "res": None, "presets": None}
    yield state
    tmp.cleanup()


# --- shared givens ---
@given("the seed presets exist")
def seed_ok(ctx):
    assert len(repo.list_presets(ctx["db"])) == 5


# --- license_generation.feature ---
@when('I generate a WAV lease for "Demo Beat" to "Demo Artist"')
def gen_wav(ctx):
    presets = {p["name"]: p for p in repo.list_presets(ctx["db"])}
    ctx["res"] = generate(_base_form(), presets["WAV Lease"], "non-exclusive")


@when("I generate with an empty customer fullname")
def gen_missing(ctx):
    presets = {p["name"]: p for p in repo.list_presets(ctx["db"])}
    ctx["res"] = generate(_base_form(CUSTOMER_FULLNAME=""), presets["WAV Lease"], "non-exclusive")


@when('I generate a lease priced "99 USD" without price words')
def gen_words(ctx):
    presets = {p["name"]: p for p in repo.list_presets(ctx["db"])}
    ctx["res"] = generate(_base_form(PRICE_AMOUNT="99", PRICE_CURRENCY="USD"), presets["Trackout Lease"], "non-exclusive")


@when("I generate an exclusive license")
def gen_excl(ctx):
    presets = {p["name"]: p for p in repo.list_presets(ctx["db"])}
    form = _base_form(PRICE_AMOUNT="500", PRICE_CURRENCY="USD", TERM_YEARS="10",
                      TERM_START="2026-10-17", TERM_END="2036-10-16",
                      PUBLISHING_SHARES="Licensor 50% / Licensee 50%",
                      ROYALTY_AMOUNT="3%")
    ctx["res"] = generate(form, presets["Exclusive"], "exclusive")


@then("the text contains the beat title and no unfilled vars")
def check_clean(ctx):
    assert "Demo Beat" in ctx["res"]["text"]
    assert ctx["res"]["missing"] == []


@then("validation passes")
def check_valid(ctx):
    assert ctx["res"]["errors"] == []


@then("validation reports CUSTOMER_FULLNAME")
def check_missing_field(ctx):
    assert "CUSTOMER_FULLNAME" in ctx["res"]["errors"]


@then('the text contains "ninety-nine USD"')
def check_words(ctx):
    assert "ninety-nine usd" in ctx["res"]["text"].lower()


@then('the text contains "25. ACCEPTANCE" and "10-year"')
def check_excl(ctx):
    assert "25. ACCEPTANCE" in ctx["res"]["text"]
    assert "10-year" in ctx["res"]["text"] or "10 year" in ctx["res"]["text"].lower()


@then("no personal data leaks")
def check_noleak(ctx):
    low = ctx["res"]["text"].lower()
    for s in FORBIDDEN:
        assert s not in low, f"leak: {s}"


# --- presets.feature ---
@when("I reseed")
def reseed(ctx):
    ensure_seed(ctx["db"])
    ctx["presets"] = repo.list_presets(ctx["db"])


@then("there are still 5 presets")
def still5(ctx):
    assert len(ctx.get("presets", repo.list_presets(ctx["db"]))) == 5


@when('I duplicate "WAV Lease" as "WAV Lease Plus"')
def dup(ctx):
    presets = {p["name"]: p for p in repo.list_presets(ctx["db"])}
    src = presets["WAV Lease"]
    ctx["new_id"] = repo.create_preset(ctx["db"], {
        "name": "WAV Lease Plus", "kind": src["kind"],
        "term_years": src["term_years"],
        "file_type": src["file_type"], "royalty": src["royalty"],
        "publishing_shares": src["publishing_shares"],
        "template_file": src["template_file"],
    })


@then('the preset list contains "WAV Lease Plus"')
def contains_plus(ctx):
    assert "WAV Lease Plus" in {p["name"] for p in repo.list_presets(ctx["db"])}


@when("I create then delete a temp preset")
def create_delete(ctx):
    nid = repo.create_preset(ctx["db"], {
        "name": "Temp X", "kind": "non-exclusive",
        "term_years": 1, "file_type": "MP3",
        "royalty": "0%", "publishing_shares": "Producer 100%",
        "template_file": "non_exclusive_lease.md",
    })
    assert repo.delete_preset(ctx["db"], nid)
    ctx["deleted"] = "Temp X"


@then("it no longer exists")
def gone(ctx):
    assert ctx["deleted"] not in {p["name"] for p in repo.list_presets(ctx["db"])}
