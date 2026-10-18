"""License policy: single source of truth for values shared across layers.

Every engine/service/database/UI module imports from here instead of repeating
literals — renaming a template, changing default caps, or switching currency
means editing one line. Dependency-free (nothing in app imports policy back).
"""

# Contract templates (bundled seeds; `_ES` variants resolved by suffix swap)
NON_EXCLUSIVE_TEMPLATE = "non_exclusive_lease.md"
EXCLUSIVE_TEMPLATE = "exclusive_10y.md"

# Per-tier caps (strings: tiers also accept "unlimited")
DEFAULT_DISTRIBUTE_COPIES = "5000"
DEFAULT_AUDIO_STREAMS = "500000"
UNLIMITED = "unlimited"

# Money
DEFAULT_CURRENCY = "USD"
CURRENCIES = ["USD", "MXN", "EUR", "GBP", "COP", "ARS", "CLP", "PEN"]
DEFAULT_PRICE_AMOUNT = "500"

# Producer credit line prefix ("Prod. by <alias>")
CREDIT_PREFIX = "Prod. by"

# Document brand (cover eyebrow + footers). Empty setting falls back to the
# producer profile alias, then to this. Filenames keep filename_prefix.
DEFAULT_BRAND = "TRAKKLICENSE"

# Folio LIC-YYYY-NNNN (counter resets each year; never reused)
FOLIO_PREFIX = "LIC-"
FOLIO_DRAFT = "DRAFT"
FOLIO_SEQ_WIDTH = 4

# Evidence (content hashes pin exact versions in history + footers)
HASH_SHORT_LEN = 8
EVIDENCE_PREFIX = "Evidence — "

# Term policy (years). QIntValidators are cosmetic — choke points clamp to this.
DEFAULT_TERM_YEARS = 10

# IPI (Interested Party Information, CISAC): 9-11 digits, leading zeros kept
IPI_PATTERN = r"\d{9,11}"

# UI/housekeeping
HISTORY_LIMIT = 50
TIER_NAME_MAX_LEN = 60
FILENAME_SEGMENT_MAX_LEN = 60
LONG_DOC_NOTICE_CHARS = 20000
