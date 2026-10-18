"""SQLite connection + schema for TRAKKLICENSE. Offline-first, stdlib only."""
import sqlite3
from pathlib import Path

from ..engine.policy import (
    DEFAULT_AUDIO_STREAMS,
    DEFAULT_DISTRIBUTE_COPIES,
    DEFAULT_TERM_YEARS,
    NON_EXCLUSIVE_TEMPLATE,
    UNLIMITED,
)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS presets(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL,
  term_years INTEGER NOT NULL DEFAULT {DEFAULT_TERM_YEARS},
  file_type TEXT NOT NULL DEFAULT 'MP3',
  royalty TEXT NOT NULL DEFAULT '0%',
  publishing_shares TEXT NOT NULL DEFAULT 'Producer retains 100%',
  template_file TEXT NOT NULL DEFAULT '{NON_EXCLUSIVE_TEMPLATE}',
  distribute_copies TEXT NOT NULL DEFAULT '{DEFAULT_DISTRIBUTE_COPIES}',
  audio_streams TEXT NOT NULL DEFAULT '{DEFAULT_AUDIO_STREAMS}'
);
CREATE TABLE IF NOT EXISTS sales(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  preset_id INTEGER REFERENCES presets(id),
  contract_date TEXT NOT NULL,
  beat_title TEXT NOT NULL,
  producer_alias TEXT NOT NULL,
  owner_fullname TEXT NOT NULL,
  producer_ipi TEXT NOT NULL DEFAULT '',
  customer_fullname TEXT NOT NULL,
  customer_alias TEXT NOT NULL DEFAULT '',
  customer_ipi TEXT NOT NULL DEFAULT '',
  customer_address TEXT NOT NULL DEFAULT '',
  price TEXT NOT NULL,
  price_words TEXT NOT NULL DEFAULT '',
  file_type TEXT NOT NULL DEFAULT '',
  term_start TEXT NOT NULL DEFAULT '',
  term_end TEXT NOT NULL DEFAULT '',
  term_years TEXT NOT NULL DEFAULT '',
  publishing_rights TEXT NOT NULL DEFAULT '',
  publishing_shares TEXT NOT NULL DEFAULT '',
  royalty TEXT NOT NULL DEFAULT '',
  samples TEXT NOT NULL DEFAULT 'None declared',
  state_country TEXT NOT NULL DEFAULT '',
  country TEXT NOT NULL DEFAULT '',
  credit TEXT NOT NULL DEFAULT '',
  rendered_text TEXT NOT NULL DEFAULT '',
  accepted_at TEXT NOT NULL DEFAULT '',
  template_version TEXT NOT NULL DEFAULT '',
  text_hash TEXT NOT NULL DEFAULT '',
  folio TEXT NOT NULL DEFAULT '',
  template_file TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def init_db(con: sqlite3.Connection):
    con.executescript(SCHEMA)
    _migrate_presets_no_price(con)
    _migrate_sales_evidence(con)
    _migrate_sales_ipi(con)
    _migrate_preset_caps(con)
    con.commit()


def _migrate_sales_ipi(con: sqlite3.Connection):
    """v0.8: structured IPI identifiers (also rendered into the contract text)."""
    cur = con.execute("PRAGMA table_info(sales)")
    cols = {r["name"] for r in cur.fetchall()}
    for col in ("producer_ipi", "customer_ipi"):
        if col not in cols:
            con.execute(f"ALTER TABLE sales ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")


def _migrate_sales_evidence(con: sqlite3.Connection):
    """v0.5: evidence cols; v0.7: folio + template_file."""
    cur = con.execute("PRAGMA table_info(sales)")
    cols = {r["name"] for r in cur.fetchall()}
    for col in ("accepted_at", "template_version", "text_hash", "folio", "template_file"):
        if col not in cols:
            con.execute(f"ALTER TABLE sales ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")


def _migrate_preset_caps(con: sqlite3.Connection):
    """Per-tier caps (copies/streams). New columns default numeric; exclusive
    tiers backfill to 'unlimited' — only while still on defaults, so user
    edits are never clobbered on restart."""
    # FIX: the backfill UPDATE used to run on EVERY init_db(). A user who
    # deliberately set an exclusive tier to 5000/500000 got clobbered back to
    # unlimited on restart. Now it runs only when the columns were just added.
    cur = con.execute("PRAGMA table_info(presets)")
    cols = {r["name"] for r in cur.fetchall()}
    added = False
    if "distribute_copies" not in cols:
        con.execute(f"ALTER TABLE presets ADD COLUMN distribute_copies TEXT NOT NULL DEFAULT '{DEFAULT_DISTRIBUTE_COPIES}'")
        added = True
    if "audio_streams" not in cols:
        con.execute(f"ALTER TABLE presets ADD COLUMN audio_streams TEXT NOT NULL DEFAULT '{DEFAULT_AUDIO_STREAMS}'")
        added = True
    if added:
        con.execute(
            f"UPDATE presets SET distribute_copies='{UNLIMITED}', audio_streams='{UNLIMITED}' "
            f"WHERE kind='exclusive' AND distribute_copies='{DEFAULT_DISTRIBUTE_COPIES}' "
            f"AND audio_streams='{DEFAULT_AUDIO_STREAMS}'"
        )


def _migrate_presets_no_price(con: sqlite3.Connection):
    """Drop legacy price/currency columns (v0.3: price moved to sale form)."""
    cur = con.execute("PRAGMA table_info(presets)")
    cols = [r["name"] if isinstance(r, dict) else r[1] for r in cur.fetchall()]
    if "price" not in cols and "currency" not in cols:
        return
    con.execute(f"""
    CREATE TABLE IF NOT EXISTS presets_new(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL,
      kind TEXT NOT NULL,
      term_years INTEGER NOT NULL DEFAULT {DEFAULT_TERM_YEARS},
      file_type TEXT NOT NULL DEFAULT 'MP3',
      royalty TEXT NOT NULL DEFAULT '0%',
      publishing_shares TEXT NOT NULL DEFAULT 'Producer retains 100%',
      template_file TEXT NOT NULL DEFAULT '{NON_EXCLUSIVE_TEMPLATE}',
      distribute_copies TEXT NOT NULL DEFAULT '{DEFAULT_DISTRIBUTE_COPIES}',
      audio_streams TEXT NOT NULL DEFAULT '{DEFAULT_AUDIO_STREAMS}'
    )""")
    # copy common columns (ignore price/currency)
    keep = ["id", "name", "kind", "term_years", "file_type",
            "royalty", "publishing_shares", "template_file"]
    have = [c for c in keep if c in cols]
    con.execute(
        f"INSERT OR IGNORE INTO presets_new({','.join(have)}) "
        f"SELECT {','.join(have)} FROM presets"
    )
    con.execute("DROP TABLE presets")
    con.execute("ALTER TABLE presets_new RENAME TO presets")
