"""Settings service: JSON file in base_dir. Offline, no personal data."""
import json
from pathlib import Path
from ..engine.policy import DEFAULT_BRAND, DEFAULT_CURRENCY, FOLIO_PREFIX, FOLIO_SEQ_WIDTH
from ..utils.paths import base_dir

FILENAME = "settings.json"

DEFAULTS = {
    "out_dir": "",               # empty = default out_dir()
    "brand_name": "",            # empty = producer alias, else DEFAULT_BRAND
    "filename_prefix": DEFAULT_BRAND,
    "filename_hash": True,       # append _{hash8} to filenames
    "filename_folio": True,      # include folio in filenames
    "folio_enabled": True,       # assign {FOLIO_PREFIX}YYYY-NNNN on save
    "folio_seq": 0,              # last used sequence (persisted counter)
    "folio_year": 0,             # year of folio_seq (resets each year)
    "footer_evidence": True,     # append Evidence line to exports
    "footer_accepted": True,     # include Accepted timestamp in footer
    "pdf_pagesize": "LETTER",    # LETTER | A4
    "pdf_cover": True,           # first cover page in PDF (title/parties/price/date/folio)
    "open_after_export": True,   # open PDF with default app after export
    "default_language": "English",
    "default_currency": DEFAULT_CURRENCY,
    "require_acceptance": True,  # block export/save without checkbox
    # Producer profile (autofill, editable in Settings)
    "profile_alias": "",
    "profile_owner": "",
    "profile_producer_ipi": "",
    # Legacy: producer location used to autofill the BUYER address (wrong party).
    # Kept so old settings.json files still load; no longer read or written by UI.
    "profile_location": "",
    "profile_state_country": "",
}


def _path() -> Path:
    return base_dir() / FILENAME


def load() -> dict:
    data = dict(DEFAULTS)
    try:
        raw = _path().read_text(encoding="utf-8")
        stored = json.loads(raw)
        for k in DEFAULTS:
            if k in stored:
                data[k] = stored[k]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    # sanitize
    if data.get("pdf_pagesize") not in ("LETTER", "A4"):
        data["pdf_pagesize"] = "LETTER"
    for k in ("filename_hash", "filename_folio", "folio_enabled",
              "footer_evidence", "footer_accepted", "pdf_cover",
              "open_after_export", "require_acceptance"):
        data[k] = bool(data.get(k))
    try:
        data["folio_seq"] = int(data.get("folio_seq") or 0)
    except (TypeError, ValueError):
        data["folio_seq"] = 0
    try:
        data["folio_year"] = int(data.get("folio_year") or 0)
    except (TypeError, ValueError):
        data["folio_year"] = 0
    data["filename_prefix"] = str(data.get("filename_prefix") or DEFAULT_BRAND).strip() or DEFAULT_BRAND
    data["brand_name"] = str(data.get("brand_name") or "").strip()
    return data


def _lock_dir() -> Path:
    return _path().with_suffix(".lock.d")


def _acquire_lock(timeout_s: float = 5.0):
    """Cross-process mkdir lock (atomic on Windows + POSIX). Yields or raises TimeoutError."""
    import time
    lock = _lock_dir()
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout_s
    while True:
        try:
            lock.mkdir(exist_ok=False)
            return lock
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError("settings locked")
            time.sleep(0.02)


def _release_lock(lock) -> None:
    try:
        lock.rmdir()
    except OSError:
        pass


def next_folio() -> str:
    """Assign next folio (counter resets each year). Returns '' if disabled."""
    # FIX: read-modify-write was racy (two exports → duplicate folios) and
    # consumed a number even when the DB save later failed. Locking removes
    # duplicates; gaps on failed saves are kept by design (folios never reused).
    import datetime
    lock = _acquire_lock()
    try:
        data = load()
        if not data.get("folio_enabled", True):
            return ""
        year = datetime.date.today().year
        seq = data.get("folio_seq", 0) + 1 if data.get("folio_year") == year else 1
        data["folio_seq"] = seq
        data["folio_year"] = year
        _write_atomic(data)
        return f"{FOLIO_PREFIX}{year}-{seq:0{FOLIO_SEQ_WIDTH}d}"
    finally:
        _release_lock(lock)


def _write_atomic(data: dict) -> dict:
    target = _path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, target)
    return data


def save(patch: dict) -> dict:
    # FIX: atomic + locked so concurrent exports can't interleave folio counters.
    lock = _acquire_lock()
    try:
        data = load()
        for k in DEFAULTS:
            if k in patch:
                data[k] = patch[k]
        return _write_atomic(data)
    finally:
        _release_lock(lock)
