"""Template library service: bundled seeds + user overrides. No Qt.

Layout:
  - bundled (read-only, ships with app): utils.paths.templates_dir()
  - custom (user-writable): <base_dir>/templates/*.md

Resolution is user-first: a custom file shadows the bundled seed with the
same name. Editing a seed uses copy-on-write (bundled files never touched,
which also works inside the frozen .exe). "Reset" deletes the override.

template_version() stays content-based, so custom edits are tracked by the
existing history evidence (template-changed warnings) with no extra code.
"""
import re
from pathlib import Path

from ..engine.renderer import find_variables
from ..engine.variables import VARIABLES
from ..utils.paths import base_dir, templates_dir

_NAME_RE = re.compile(r"^[\w\-]+\.md$")


def sanitize_name(name: str) -> str:
    """'Mi plantilla' → 'Mi_plantilla.md'. Valid names pass through untouched.

    Raises ValueError when unusable.
    """
    raw = str(name or "").strip()
    if _NAME_RE.match(raw):
        return raw
    stem = re.sub(r"\.md$", "", raw, flags=re.IGNORECASE)
    s = re.sub(r"[^\w\- ]+", "", stem, flags=re.UNICODE).strip().replace(" ", "_")
    if not s:
        raise ValueError("empty template name")
    s = s + ".md"
    if not _NAME_RE.match(s) or len(s) > 64:
        raise ValueError(f"bad template name: {name!r}")
    return s


def _check_safe(name: str) -> str:
    if not _NAME_RE.match(name or ""):
        raise FileNotFoundError(f"bad template name: {name!r}")
    return name


def user_templates_dir() -> Path:
    d = base_dir() / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_templates() -> list[dict]:
    """Merged library. Each item: {name, source: bundled|override|custom}."""
    bundled = {p.name for p in templates_dir().glob("*.md")}
    try:
        custom = {p.name for p in user_templates_dir().glob("*.md")}
    except OSError:
        custom = set()
    out = []
    for name in sorted(bundled | custom):
        if name in custom and name in bundled:
            source = "override"
        elif name in custom:
            source = "custom"
        else:
            source = "bundled"
        out.append({"name": name, "source": source})
    return out


def template_exists(name: str) -> bool:
    try:
        _check_safe(name)
    except FileNotFoundError:
        return False
    return (user_templates_dir() / name).is_file() or (templates_dir() / name).is_file()


def resolve_template(name: str) -> Path:
    """User-first path. Raises FileNotFoundError when missing/blocked."""
    _check_safe(name)
    user = user_templates_dir() / name
    if user.is_file():
        return user
    bundled = templates_dir() / name
    if bundled.is_file():
        return bundled
    raise FileNotFoundError(f"template not found: {name}")


def read_template(name: str) -> str:
    # utf-8-sig: seed files carry a BOM; strip it so the first-line
    # heading ("# ...") renders as a heading, not a body paragraph.
    return resolve_template(name).read_text(encoding="utf-8-sig")


def write_template(name: str, text: str) -> Path:
    """Save (or create) a user template. Copy-on-write for bundled seeds.

    Human-friendly names are sanitized ('Mi plantilla' → 'Mi_plantilla.md').
    """
    name = sanitize_name(name)
    p = user_templates_dir() / name
    p.write_text(text, encoding="utf-8")
    return p


def delete_template(name: str) -> bool:
    """Delete a pure-custom template. Returns False for bundled/overrides (use reset)."""
    _check_safe(name)
    if (templates_dir() / name).is_file():
        return False
    p = user_templates_dir() / name
    if not p.is_file():
        return False
    p.unlink()
    return True


def reset_template(name: str) -> bool:
    """Drop the user override, back to the bundled seed. False when nothing to reset."""
    _check_safe(name)
    if not (templates_dir() / name).is_file():
        return False
    p = user_templates_dir() / name
    if not p.is_file():
        return False
    p.unlink()
    return True


def validate_template(text: str) -> dict:
    """Static checks before save. Never raises on weird input.

    Returns {used, unknown, if_open, if_close, unbalanced_if}.
    `unknown` vars would render literally in the client contract.
    """
    used = find_variables(text or "")
    unknown = sorted(used - set(VARIABLES))
    if_open = len(re.findall(r"\{IF\b", text or "", flags=re.IGNORECASE))
    if_close = len(re.findall(r"\{ENDIF\}", text or "", flags=re.IGNORECASE))
    return {"used": sorted(used), "unknown": unknown,
            "if_open": if_open, "if_close": if_close,
            "unbalanced_if": if_open != if_close}
