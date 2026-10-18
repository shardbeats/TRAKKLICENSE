"""Template library: user-first resolution, copy-on-write, validation."""
import pytest

from app.services import template_service as tpls


def test_list_shows_bundled_seeds():
    names = {t["name"] for t in tpls.list_templates()}
    assert {"non_exclusive_lease.md", "exclusive_10y.md"} <= names
    assert all(t["source"] == "bundled" for t in tpls.list_templates()
               if t["name"] in ("non_exclusive_lease.md", "exclusive_10y.md"))


def test_user_shadows_bundled(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    assert tpls.resolve_template("non_exclusive_lease.md").parent.name == "seed_templates"
    tpls.write_template("non_exclusive_lease.md", "# custom")
    assert tpls.resolve_template("non_exclusive_lease.md").read_text() == "# custom"
    assert tpls.list_templates()[0]["source"] in ("bundled", "custom", "override")
    src = {t["name"]: t["source"] for t in tpls.list_templates()}
    assert src["non_exclusive_lease.md"] == "override"
    # bundled seed file untouched
    from app.utils.paths import templates_dir
    assert "custom" not in (templates_dir() / "non_exclusive_lease.md").read_text()
    assert tpls.reset_template("non_exclusive_lease.md") is True
    assert {t["name"]: t["source"] for t in tpls.list_templates()}["non_exclusive_lease.md"] == "bundled"


def test_custom_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    p = tpls.write_template("Mi Plantilla", "hello {PRODUCT_TITLE}")
    assert p.name == "Mi_Plantilla.md"
    assert tpls.read_template("Mi_Plantilla.md") == "hello {PRODUCT_TITLE}"
    assert tpls.reset_template("Mi_Plantilla.md") is False  # pure custom: reset N/A
    assert tpls.delete_template("Mi_Plantilla.md") is True
    assert tpls.delete_template("Mi_Plantilla.md") is False
    assert tpls.delete_template("non_exclusive_lease.md") is False  # bundled protected
    with pytest.raises(ValueError):
        tpls.sanitize_name("///")
    with pytest.raises(FileNotFoundError):
        tpls.read_template("../evil.md")
    with pytest.raises(FileNotFoundError):
        tpls.read_template("nope.md")


def test_bom_stripped_for_render(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    text = tpls.read_template("non_exclusive_lease.md")
    assert "\ufeff" not in text
    assert text.startswith("# NON-EXCLUSIVE")


def test_validate_spots_unknown_and_if():
    rep = tpls.validate_template("Hi {PRODUCT_TITLE} and {NOPE_VAR} {IF X}yo{ENDIF}")
    assert "NOPE_VAR" in rep["unknown"]
    assert "PRODUCT_TITLE" in rep["used"] and "PRODUCT_TITLE" not in rep["unknown"]
    assert rep["unbalanced_if"] is False
    bad = tpls.validate_template("{IF A}open {IF B}open{ENDIF}")
    assert bad["unbalanced_if"] is True
    assert tpls.validate_template("")["unknown"] == []


def test_generate_prefers_user_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    from app.services.generation import generate
    tpls.write_template("non_exclusive_lease.md", "# MINE {PRODUCT_TITLE}")
    res = generate({"PRODUCT_TITLE": "B"}, {"name": "L",
                   "template_file": "non_exclusive_lease.md"}, "non-exclusive")
    assert res["text"].startswith("# MINE")
    tpls.reset_template("non_exclusive_lease.md")
