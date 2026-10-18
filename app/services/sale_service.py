"""Sale service: folio assignment + re-render + persist. No Qt, no file I/O beyond DB."""
from datetime import datetime

from ..database.repositories import save_sale
from ..services.generation import generate
from ..services.settings import next_folio
from ..utils.paths import db_path


def save_current_sale(form: dict, preset: dict | None, preset_id, db=None) -> dict:
    """Assign folio, re-render (so FOLIO+hash belong to final text) and persist.

    Returns {"sale_id": int, "folio": str, "res": dict}.
    """
    folio = next_folio()
    # Always stamp FOLIO ("" when disabled) so saved text never says DRAFT by accident
    form = {**form, "FOLIO": folio}
    kind = (preset or {}).get("kind", "non-exclusive")
    res = generate(form, preset, kind)
    d = res["data"]
    sale = {
        "preset_id": preset_id,
        "contract_date": d.get("CONTRACT_DATE", ""),
        "beat_title": d.get("PRODUCT_TITLE", ""),
        "producer_alias": d.get("PRODUCER_ALIAS", ""),
        "owner_fullname": d.get("PRODUCT_OWNER_FULLNAME", ""),
        "producer_ipi": d.get("PRODUCER_IPI", ""),
        "customer_fullname": d.get("CUSTOMER_FULLNAME", ""),
        "customer_alias": d.get("CUSTOMER_ALIAS", ""),
        "customer_ipi": d.get("CUSTOMER_IPI", ""),
        "customer_address": d.get("CUSTOMER_ADDRESS", ""),
        "price": d.get("PRODUCT_PRICE", ""),
        "price_words": d.get("PRODUCT_PRICE_WORD", ""),
        "file_type": d.get("FILE_TYPE", ""),
        "term_start": d.get("TERM_START", ""),
        "term_end": d.get("TERM_END", ""),
        "term_years": d.get("TERM_YEARS", ""),
        "publishing_rights": d.get("PUBLISHING_RIGHTS", ""),
        "publishing_shares": d.get("PUBLISHING_SHARES", ""),
        "royalty": d.get("ROYALTY_AMOUNT", ""),
        "samples": d.get("SAMPLES", ""),
        "state_country": d.get("STATE_PROVINCE_COUNTRY", ""),
        "country": d.get("COUNTRY", ""),
        "credit": d.get("CREDIT_LINE", ""),
        "rendered_text": res["text"],
        "accepted_at": datetime.now().isoformat(timespec="seconds"),
        "template_version": res.get("template_version", ""),
        "text_hash": res.get("text_hash", ""),
        "folio": folio,
        "template_file": res.get("template_file", ""),
    }
    sid = save_sale(db or db_path(), sale)
    return {"sale_id": sid, "folio": folio, "res": res}
