"""Scan every seed template: all vars known + no personal data."""
from pathlib import Path
from app.engine.variables import VARIABLES
from app.engine.renderer import find_variables

FORBIDDEN = ["juan perez garcia", "estudio demo records", "00012345678",
             "ciudad ficticia", "mc prueba", "lopez hernandez", "beat de ejemplo"]
ROOT = Path(__file__).resolve().parents[1]


def test_all_templates_clean():
    for tpl in (ROOT / "app" / "seed_templates").glob("*.md"):
        src = tpl.read_text(encoding="utf-8")
        low = src.lower()
        for s in FORBIDDEN:
            assert s not in low, f"{tpl.name} leaks {s}"
        for v in find_variables(src):
            assert v in VARIABLES or v in ("VAR",), f"{tpl.name}: unknown var {v}"
