"""Document service: filename options, evidence footer, PDF cover, out dir. No Qt."""
from datetime import datetime
from pathlib import Path

from ..engine.policy import DEFAULT_BRAND, EVIDENCE_PREFIX, HASH_SHORT_LEN
from ..services.generation import sha256_text
from ..utils.paths import out_dir


def brand_name(settings: dict, form_alias: str = "") -> str:
    """Document brand: explicit setting → sale-form alias → profile alias → default.

    The form alias (the licensor actually named in this contract) wins over the
    profile: the brand on the PDF must match the licensor in the text. Filenames
    keep using filename_prefix, which serves file organization instead.
    """
    explicit = (settings.get("brand_name") or "").strip()
    if explicit:
        return explicit
    sale_alias = (form_alias or "").strip()
    if sale_alias:
        return sale_alias
    alias = (settings.get("profile_alias") or "").strip()
    if alias:
        return alias
    return DEFAULT_BRAND


def resolve_out_dir(settings: dict) -> Path:
    custom = (settings.get("out_dir") or "").strip()
    if custom:
        p = Path(custom)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return out_dir()


def evidence_footer(settings: dict, res: dict) -> str:
    """Integrity footer: document hash (+ acceptance timestamp). The template
    revision stays in the history record (History warns on template change),
    not in the client-facing document — a bare "Template v…" hash means
    nothing to the artist and only adds noise to a legal text."""
    if not settings.get("footer_evidence", True):
        return ""
    parts = [f"SHA256: {res.get('text_hash', '')}"]
    if settings.get("footer_accepted", True):
        parts.append(f"Accepted: {datetime.now().isoformat(timespec='seconds')}")
    return EVIDENCE_PREFIX + " | ".join(parts)


def file_options(settings: dict, last_data: dict, res: dict, last_text: str = "") -> tuple[str, str, str]:
    """Returns (hash8, prefix, folio) for export filename builders."""
    full_hash = res.get("text_hash", "") or (sha256_text(last_text) if last_text else "")
    hash8 = full_hash[:HASH_SHORT_LEN] if settings.get("filename_hash", True) else ""
    folio = (last_data.get("FOLIO", "") or "").strip()
    # Filenames drop the folio only when filename_folio is off. DRAFT is kept
    # for preview files; exports auto-save first so they already carry a real folio.
    if not settings.get("filename_folio", True):
        folio = ""
    prefix = settings.get("filename_prefix", "TRAKKLICENSE")
    return hash8, prefix, folio


def cover_data(settings: dict, last_data: dict, res: dict) -> dict | None:
    if not settings.get("pdf_cover", True):
        return None
    prod = f"{last_data.get('PRODUCER_ALIAS', '')} ({last_data.get('PRODUCT_OWNER_FULLNAME', '')})"
    if str(last_data.get("PRODUCER_IPI", "")).strip():
        prod += f" — IPI {str(last_data.get('PRODUCER_IPI', '')).strip()}"
    cust = f"{last_data.get('CUSTOMER_ALIAS', '')} ({last_data.get('CUSTOMER_FULLNAME', '')})"
    if str(last_data.get("CUSTOMER_IPI", "")).strip():
        cust += f" — IPI {str(last_data.get('CUSTOMER_IPI', '')).strip()}"
    return {
        "title": str(last_data.get("LICENSE_NAME", "")).strip() or "Beat License",
        "rows": [
            ("Folio", last_data.get("FOLIO", "")),
            ("Beat", last_data.get("PRODUCT_TITLE", "")),
            ("Producer", prod),
            ("Customer", cust),
            ("Price", f"{last_data.get('PRODUCT_PRICE', '')} ({last_data.get('PRODUCT_PRICE_WORD', '')})"),
            ("Date", last_data.get("CONTRACT_DATE", "")),
            ("Term", f"{last_data.get('TERM_YEARS', '')} years ({last_data.get('TERM_START', '')} → {last_data.get('TERM_END', '')})"),
            ("SHA256", res.get("text_hash", "")),
        ],
    }


def open_file(path: Path):
    """Best-effort open with default OS app. Never raises."""
    import os
    import subprocess
    import sys
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass
