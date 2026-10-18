"""Generation service: form + preset → render data → text. No GUI imports."""
import datetime
import hashlib
from pathlib import Path
from ..engine.policy import (
    CREDIT_PREFIX,
    CURRENCIES,
    DEFAULT_CURRENCY,
    EXCLUSIVE_TEMPLATE,
    FOLIO_DRAFT,
    HASH_SHORT_LEN,
    NON_EXCLUSIVE_TEMPLATE,
)
from ..engine.renderer import render
from ..engine.money_words import money_to_words, number_to_words
from ..engine.validators import validate


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def template_version(template_file: str) -> str:
    """First 8 of sha256 of template source. Tracks exact version sold."""
    from ..services.template_service import read_template
    try:
        src = read_template(template_file)
    except (FileNotFoundError, ValueError):
        src = ""
    return sha256_text(src)[:HASH_SHORT_LEN]


def today_iso() -> str:
    return datetime.date.today().isoformat()


#: Legal display names — contracts show these, never the commercial tier name
#: ("WAV Lease", "Exclusive 10Y" stay inside the app).
LICENSE_DISPLAY = {
    "exclusive": "Exclusive License",
    "non-exclusive": "Non-Exclusive License",
}
LICENSE_DISPLAY_ES = {
    "exclusive": "Licencia Exclusiva",
    "non-exclusive": "Licencia No Exclusiva",
}


def license_display_name(kind: str | None, lang: str = "en") -> str:
    table = LICENSE_DISPLAY_ES if str(lang).lower().startswith("es") else LICENSE_DISPLAY
    return table.get(str(kind or "").lower(), table["non-exclusive"])


def compute_term_end(start: str, years) -> str:
    """TERM_START (YYYY-MM-DD) + N years → TERM_END ISO. "" when unparsable.

    Feb 29 lands on Feb 28 on non-leap years. Non-positive years and overflow
    also yield "" — the UI caps input at 1..100.
    """
    try:
        d = datetime.date.fromisoformat(str(start).strip())
        n = int(str(years).strip())
    except (ValueError, TypeError):
        return ""
    if n <= 0:
        return ""
    try:
        return d.replace(year=d.year + n).isoformat()
    except ValueError:
        try:
            return d.replace(year=d.year + n, day=28).isoformat()
        except ValueError:  # e.g. Feb 29 → Feb 28 fails, or year overflow past 9999
            return ""


def compose_samples(items: list[tuple[str, str]], confirmed: bool) -> str:
    """BeatStars-style loops/samples list. Returns 'None declared' when unchecked.

    items: [(name, source), ...]. Empty names dropped.
    """
    if not confirmed:
        return "None declared"
    clean = [(n.strip(), s.strip()) for n, s in items if n.strip()]
    if not clean:
        return "None declared — box checked but no items listed"
    parts = []
    for i, (n, s) in enumerate(clean, 1):
        parts.append(f"{i}. {n} — Source: {s or 'unspecified'}")
    return "; ".join(parts)


def build_render_data(form: dict, preset: dict | None = None) -> dict:
    """Merge form + preset defaults + auto *_WORD fields.

    Price lives in the sale form (PRICE_AMOUNT + PRICE_CURRENCY),
    never in the preset. PRODUCT_PRICE is composed here for templates.
    """
    data = dict(form)
    if preset:
        # FIX: setdefault() ignores keys that exist with "" — the UI always sends
        # every field (empty string when untouched), so an empty form field must
        # fall back to the tier value instead of rendering a blank contract line.
        for dst, src in (("FILE_TYPE", "file_type"),
                         ("ROYALTY_AMOUNT", "royalty"),
                         ("PUBLISHING_SHARES", "publishing_shares"),
                         ("DISTRIBUTE_COPIES", "distribute_copies"),
                         ("AUDIO_STREAMS", "audio_streams")):
            if not str(data.get(dst, "")).strip():
                val = preset.get(src, "")
                if str(val or "").strip() != "":
                    data[dst] = str(val)
        if not str(data.get("TERM_YEARS", "")).strip():
            data["TERM_YEARS"] = str(preset.get("term_years", ""))
    # LICENSE_NAME is a legal term derived from kind ("Exclusive License"),
    # never the commercial tier name ("WAV Lease", "Exclusive 10Y").
    if not str(data.get("LICENSE_NAME", "")).strip():
        data["LICENSE_NAME"] = license_display_name(
            (preset or {}).get("kind", "non-exclusive"))
    # Compose price from amount + currency inputs (sale-level, editable)
    if not data.get("PRODUCT_PRICE"):
        amount = str(data.get("PRICE_AMOUNT", "")).strip()
        currency = str(data.get("PRICE_CURRENCY", "")).strip().upper() or DEFAULT_CURRENCY
        if amount:
            data["PRODUCT_PRICE"] = f"{amount} {currency}".strip()
    # auto WORD fields (non-numeric values like "unlimited" pass through as-is)
    raw_copies = str(data.get("DISTRIBUTE_COPIES", "")).strip()
    if raw_copies and not data.get("DISTRIBUTE_COPIES_WORD"):
        try:
            data["DISTRIBUTE_COPIES_WORD"] = number_to_words(int(raw_copies.replace(",", "")), "en")
        except (ValueError, TypeError):
            data["DISTRIBUTE_COPIES_WORD"] = raw_copies
    raw_streams = str(data.get("AUDIO_STREAMS", "")).strip()
    if raw_streams and not data.get("AUDIO_STREAMS_WORD"):
        try:
            data["AUDIO_STREAMS_WORD"] = number_to_words(int(raw_streams.replace(",", "")), "en")
        except (ValueError, TypeError):
            data["AUDIO_STREAMS_WORD"] = raw_streams
    if data.get("PRODUCT_PRICE") and not data.get("PRODUCT_PRICE_WORD"):
        # try parse numeric prefix
        import re
        m = re.search(r"([\d.,]+)", str(data["PRODUCT_PRICE"]))
        if m:
            try:
                amt = float(m.group(1).replace(",", ""))
                upper = str(data["PRODUCT_PRICE"]).upper()
                cur = next((c for c in CURRENCIES if c in upper), "")
                if not cur:
                    cur = str(data.get("PRICE_CURRENCY", "")).strip().upper() or DEFAULT_CURRENCY
                data["PRODUCT_PRICE_WORD"] = money_to_words(amt, "en", cur)
            except Exception:
                pass
    data.setdefault("CREDIT_LINE", f"{CREDIT_PREFIX} {data.get('PRODUCER_ALIAS','')}".strip())
    data.setdefault("FOLIO", FOLIO_DRAFT)
    # TERM_START auto: the term runs from the effective date
    # ("as of the date of purchase", BeatStars-style). Explicit API values respected.
    if not str(data.get("TERM_START", "")).strip() and str(data.get("CONTRACT_DATE", "")).strip():
        data["TERM_START"] = str(data.get("CONTRACT_DATE")).strip()
    # TERM_END auto: blank end + start + years → computed (explicit values respected)
    if not str(data.get("TERM_END", "")).strip() and str(data.get("TERM_START", "")).strip():
        auto_end = compute_term_end(data.get("TERM_START", ""), data.get("TERM_YEARS", ""))
        if auto_end:
            data["TERM_END"] = auto_end
    # COUNTRY auto: last segment of "State, Country" ("Texas, USA" → "USA").
    # Explicit values (API/custom templates) are respected.
    if not str(data.get("COUNTRY", "")).strip():
        state = str(data.get("STATE_PROVINCE_COUNTRY", ""))
        data["COUNTRY"] = state.rsplit(",", 1)[-1].strip() if "," in state else state.strip()
    # FIX (#1 integridad): every known variable defaults to "" so the renderer
    # never leaves a literal "{VAR}" in the contract for known keys. Unknown
    # vars still surface via render()[1] (missing) and template validation.
    try:
        from ..engine.variables import VARIABLES as _VARIABLES
        for _k in _VARIABLES:
            data.setdefault(_k, "")
    except Exception:
        pass
    return data


def load_template(template_file: str) -> str:
    from ..services.template_service import read_template
    return read_template(template_file)


def generate(form: dict, preset: dict | None = None, license_kind: str = "non-exclusive") -> dict:
    """Returns {text, missing, errors, data, template_file, template_version, text_hash}."""
    data = build_render_data(form, preset)
    errors = validate(data, license_kind)
    # extra guard: if samples box checked, require at least one named item.
    # compose_samples() never returns "" (uses "None declared…" markers), so
    # detect the checked-but-empty marker explicitly.
    if str(data.get("SAMPLES_CONFIRMED", "")).lower() in ("1", "true", "yes"):
        samples_text = str(data.get("SAMPLES", "")).strip()
        if not samples_text or "box checked" in samples_text:
            errors = errors + ["SAMPLES"]
    template_file = (preset or {}).get("template_file") or (EXCLUSIVE_TEMPLATE if license_kind == "exclusive" else NON_EXCLUSIVE_TEMPLATE)
    try:
        tpl = load_template(template_file)
    except (FileNotFoundError, ValueError):
        template_file = NON_EXCLUSIVE_TEMPLATE
        tpl = load_template(template_file)
    # Spanish contracts use the Spanish legal term (only when auto-derived,
    # explicit user values are respected).
    if template_file.endswith("_ES.md"):
        if data.get("LICENSE_NAME") == LICENSE_DISPLAY["exclusive"]:
            data["LICENSE_NAME"] = LICENSE_DISPLAY_ES["exclusive"]
        elif data.get("LICENSE_NAME") == LICENSE_DISPLAY["non-exclusive"]:
            data["LICENSE_NAME"] = LICENSE_DISPLAY_ES["non-exclusive"]
    text, missing = render(tpl, data)
    ver = sha256_text(tpl)[:HASH_SHORT_LEN]
    return {"text": text, "missing": sorted(missing), "errors": errors, "data": data,
            "template_file": template_file, "template_version": ver,
            "text_hash": sha256_text(text)}
