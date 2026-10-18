"""Validators: required fields per license type. Pure functions."""

REQUIRED_BASE = [
    "CONTRACT_DATE", "PRODUCT_TITLE", "PRODUCER_ALIAS",
    "PRODUCT_OWNER_FULLNAME", "CUSTOMER_FULLNAME",
    "LICENSE_NAME", "PRODUCT_PRICE",
]

REQUIRED_EXCLUSIVE = REQUIRED_BASE + [
    "TERM_YEARS", "TERM_START", "TERM_END",
    "STATE_PROVINCE_COUNTRY",
]


def validate(data: dict, license_kind: str = "non-exclusive") -> list[str]:
    """Return list of missing required keys (empty = ok)."""
    kind = str(license_kind or "non-exclusive").strip().lower()
    req = REQUIRED_EXCLUSIVE if kind == "exclusive" else REQUIRED_BASE
    missing = []
    for k in req:
        v = data.get(k, "")
        if str(v).strip() in ("", "N/A"):
            # allow N/A for address only — address not in required anyway
            missing.append(k)
    return missing
