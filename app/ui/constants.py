"""Shared UI constants. Single source of truth for form fields and view policy.

Cross-layer values (currencies, caps, terms) live in engine.policy and are
re-exported here for views — never redefined.
"""
from ..engine.policy import (  # noqa: F401 (re-export)
    CURRENCIES,
    DEFAULT_AUDIO_STREAMS,
    DEFAULT_CURRENCY,
    DEFAULT_DISTRIBUTE_COPIES,
    DEFAULT_PRICE_AMOUNT,
    DEFAULT_TERM_YEARS,
)

FIELDS: list[tuple[str, str, str]] = [
    ("CONTRACT_DATE", "Effective date", ""),  # runtime default: today; term runs from here
    ("PRODUCT_TITLE", "Beat title", "Demo Beat"),
    ("PRODUCER_ALIAS", "Producer alias", ""),
    ("PRODUCT_OWNER_FULLNAME", "Owner fullname", ""),
    ("CUSTOMER_FULLNAME", "Customer fullname", ""),
    ("CUSTOMER_ALIAS", "Customer alias", ""),
    ("CUSTOMER_ADDRESS", "Customer address", ""),
    ("FILE_TYPE", "File type", "WAV + stems"),
    ("TERM_YEARS", "Term (years)", str(DEFAULT_TERM_YEARS)),  # sale data: tier default, user-editable
    ("TERM_END", "Term end", ""),  # runtime: auto = effective date + years (read-only)
    ("STATE_PROVINCE_COUNTRY", "State, Country", ""),
    ("PUBLISHING_RIGHTS", "Publishing rights", "50/50 split"),
    ("PUBLISHING_SHARES", "Publishing shares", "Licensor 50% / Licensee 50%"),
    ("ROYALTY_AMOUNT", "Master royalty", "3%"),
    ("DISTRIBUTE_COPIES", "Copies", DEFAULT_DISTRIBUTE_COPIES),
    ("AUDIO_STREAMS", "Streams", DEFAULT_AUDIO_STREAMS),
]

#: Term policy (years). The QIntValidator on inputs is cosmetic — Qt lets
#: out-of-range text through typing/paste/setText, so MainWindow/PresetsView
#: clamp to this range at the choke points. Single source of truth.
TERM_MIN_YEARS = 1
TERM_MAX_YEARS = 100

#: Live-preview debounce (ms). Exports flush pending previews first.
PREVIEW_DEBOUNCE_MS = 400

VIEW_NAMES = ("Generator", "History", "Presets", "Templates")
VIEW_SHORTCUTS = ("Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4")
