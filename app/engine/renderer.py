"""Template renderer: supports {VAR} (BeatStars) and {{var}} (TRAKK) syntax.

- Case-insensitive keys, stripped whitespace.
- Alias resolution via variables.ALIASES.
- Missing keys left as-is + reported in `missing` set.
- Minimal {IF x} / {ENDIF} support: {IF KEY}...{ENDIF} renders block
  only if KEY is truthy and not 'no'/'0'/'false'.
Pure Python, zero GUI deps.
"""
import re

from .variables import ALIASES

PAT_BRACE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
PAT_DOUBLE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
PAT_IF = re.compile(r"\{IF\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*'([^']*)')?\}", re.IGNORECASE)
PAT_ENDIF = re.compile(r"\{ENDIF\}", re.IGNORECASE)


def _norm_key(k: str) -> str:
    k = k.strip().upper()
    return ALIASES.get(k, k)


def _lookup(key: str, data: dict):
    ck = _norm_key(key)
    # direct (upper), then case-insensitive scan
    if ck in data:
        return data[ck]
    for dk, dv in data.items():
        if dk.strip().upper() == ck:
            return dv
    return None


def _eval_if(key: str, expected, data: dict) -> bool:
    val = _lookup(key, data)
    if val is None:
        return False
    s = str(val).strip()
    if expected is not None:
        return s.lower() == expected.lower()
    return s.lower() not in ("", "0", "no", "false", "none", "n/a")


def render(template: str, data: dict) -> tuple[str, set]:
    """Render template. Returns (text, missing_keys)."""
    missing: set = set()

    # Handle IF/ENDIF blocks (single-level, non-nested)
    out_parts = []
    pos = 0
    while True:
        m = PAT_IF.search(template, pos)
        if not m:
            out_parts.append(template[pos:])
            break
        out_parts.append(template[pos:m.start()])
        key, expected = m.group(1), m.group(2)
        e = PAT_ENDIF.search(template, m.end())
        if not e:
            # no ENDIF → treat rest as block
            block = template[m.end():]
            end = len(template)
        else:
            block = template[m.end():e.start()]
            end = e.end()
        if _eval_if(key, expected, data):
            out_parts.append(block)
        # else drop block
        pos = end
    text = "".join(out_parts)

    def _rep_double(m):
        key = m.group(1)
        val = _lookup(key, data)
        if val is None:
            missing.add(_norm_key(key))
            return m.group(0)
        return str(val)

    def _rep_single(m):
        key = m.group(1)
        # skip IF/ENDIF already processed (they are gone), but guard anyway
        if key.upper() in ("IF", "ENDIF"):
            return m.group(0)
        val = _lookup(key, data)
        if val is None:
            missing.add(_norm_key(key))
            return m.group(0)
        return str(val)

    text = PAT_DOUBLE.sub(_rep_double, text)
    text = PAT_BRACE.sub(_rep_single, text)
    return text, missing


def find_variables(template: str) -> set:
    """List all variable names found in template (normalized, aliases resolved)."""
    found = set()
    for m in PAT_DOUBLE.finditer(template):
        found.add(_norm_key(m.group(1)))
    # remove IF conditions from single-brace scan
    tmp = PAT_IF.sub("", template)
    tmp = PAT_ENDIF.sub("", tmp)
    for m in PAT_BRACE.finditer(tmp):
        found.add(_norm_key(m.group(1)))
    return found
