"""Seed 5 tiers (no price — price is a sale input). INSERT OR IGNORE — never overwrite user edits.

Term policy (BeatStars-style): every tier defaults to 10 years; the term is
sale data (Generator "Term (years)" field), not tier identity — hence plain
names like "Exclusive", never "Exclusive 10Y".
"""
from ..engine.policy import (
    DEFAULT_AUDIO_STREAMS,
    DEFAULT_DISTRIBUTE_COPIES,
    DEFAULT_TERM_YEARS,
    EXCLUSIVE_TEMPLATE,
    NON_EXCLUSIVE_TEMPLATE,
    UNLIMITED,
)
from .connection import get_connection, init_db

_TY = DEFAULT_TERM_YEARS
_NX = NON_EXCLUSIVE_TEMPLATE
_DC, _AS = DEFAULT_DISTRIBUTE_COPIES, DEFAULT_AUDIO_STREAMS
SEED_PRESETS = [
    ("MP3 Lease", "non-exclusive", _TY, "Tagged MP3 + Untagged MP3", "0%", "Producer retains 100%", _NX, _DC, _AS),
    ("WAV Lease", "non-exclusive", _TY, "Tagged MP3 + Untagged MP3 + Untagged WAV", "0%", "Producer retains 100%", _NX, _DC, _AS),
    ("Trackout Lease", "non-exclusive", _TY, "MP3 + WAV + stems (24-bit WAV)", "0%", "Producer retains 100%", _NX, _DC, _AS),
    ("Unlimited Lease", "non-exclusive", _TY, "MP3 + WAV + stems + unlimited streams", "0%", "Producer retains 100%", _NX, _DC, _AS),
    ("Exclusive", "exclusive", _TY, "WAV + stems", "3%", "Licensor 50% / Licensee 50%", EXCLUSIVE_TEMPLATE, UNLIMITED, UNLIMITED),
]

# Original v0.x seed rows (pre-10Y policy). Literals below are HISTORICAL DATA
# (what old DBs contain), not policy — do not replace with policy constants.
# Used ONLY to migrate pristine rows: a row is migrated iff every column still
# matches the legacy seed, so user edits are never touched.
LEGACY_SEEDS = [
    ("MP3 Lease", "non-exclusive", 5, "Tagged MP3 + Untagged MP3", "0%", "Producer retains 100%", "non_exclusive_lease.md"),
    ("WAV Lease", "non-exclusive", 5, "Tagged MP3 + Untagged MP3 + Untagged WAV", "0%", "Producer retains 100%", "non_exclusive_lease.md"),
    ("Trackout Lease", "non-exclusive", 5, "MP3 + WAV + stems (24-bit WAV)", "0%", "Producer retains 100%", "non_exclusive_lease.md"),
    ("Exclusive 10Y", "exclusive", 10, "WAV + stems + instrumental", "3%", "Licensor 50% / Licensee 50%", "exclusive_10y.md"),
]


def ensure_seed(db_path):
    con = get_connection(db_path)
    try:
        init_db(con)
        # renames first: a legacy "Exclusive 10Y" must become "Exclusive"
        # BEFORE the seed insert, or INSERT OR IGNORE would duplicate the tier.
        _migrate_preset_name(con)
        for row in SEED_PRESETS:
            con.execute(
                "INSERT OR IGNORE INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file,distribute_copies,audio_streams) VALUES(?,?,?,?,?,?,?,?,?)",
                row,
            )
        _migrate_seed_terms(con)
        _migrate_exclusive_files(con)
        con.commit()
    finally:
        con.close()


def _migrate_preset_name(con):
    """'Exclusive 10Y' → 'Exclusive' (term left the name). Skipped when the
    target name is taken (user's own preset wins)."""
    con.execute(
        "UPDATE presets SET name='Exclusive' WHERE name='Exclusive 10Y' "
        "AND NOT EXISTS (SELECT 1 FROM presets WHERE name='Exclusive')"
    )


def _migrate_seed_terms(con):
    """5 → 10 years on pristine legacy rows only (full-row match, see LEGACY_SEEDS)."""
    for name, kind, term, file_type, royalty, publishing, template in LEGACY_SEEDS:
        if term >= 10:
            continue
        con.execute(
            f"UPDATE presets SET term_years={DEFAULT_TERM_YEARS} WHERE name=? AND kind=? "
            "AND term_years=? AND file_type=? AND royalty=? "
            "AND publishing_shares=? AND template_file=?",
            (name, kind, term, file_type, royalty, publishing, template),
        )


def _migrate_exclusive_files(con):
    """'WAV + stems + instrumental' → 'WAV + stems' on pristine Exclusive rows
    only (full-row match — user edits never touched). Runs after the 10Y rename,
    so legacy rows are already called 'Exclusive' here."""
    # Historical row values stay literal (see LEGACY_SEEDS note); the template
    # file matches the current exclusive seed, so the constant applies.
    con.execute(
        "UPDATE presets SET file_type='WAV + stems' WHERE name='Exclusive' "
        f"AND kind='exclusive' AND term_years={DEFAULT_TERM_YEARS} "
        "AND file_type='WAV + stems + instrumental' AND royalty='3%' "
        "AND publishing_shares='Licensor 50% / Licensee 50%' "
        f"AND template_file='{EXCLUSIVE_TEMPLATE}'"
    )
