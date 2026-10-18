"""Repositories: presets + sales. No GUI imports."""
from pathlib import Path
from ..engine.policy import (
    DEFAULT_AUDIO_STREAMS,
    DEFAULT_DISTRIBUTE_COPIES,
    DEFAULT_TERM_YEARS,
    HISTORY_LIMIT,
    NON_EXCLUSIVE_TEMPLATE,
)
from .connection import get_connection, init_db


def list_presets(db_path: Path) -> list[dict]:
    con = get_connection(db_path)
    try:
        init_db(con)
        cur = con.execute("SELECT * FROM presets ORDER BY name ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


def get_preset(db_path: Path, preset_id: int) -> dict | None:
    con = get_connection(db_path)
    try:
        init_db(con)
        cur = con.execute("SELECT * FROM presets WHERE id=?", (preset_id,))
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def save_sale(db_path: Path, sale: dict) -> int:
    con = get_connection(db_path)
    try:
        init_db(con)
        # evidence fields default to '' for backward compat
        for k in ("producer_ipi", "customer_ipi",
                  "accepted_at", "template_version", "text_hash", "folio", "template_file"):
            sale.setdefault(k, "")
        cur = con.execute(
            """INSERT INTO sales(preset_id,contract_date,beat_title,producer_alias,owner_fullname,
            producer_ipi,customer_fullname,customer_alias,customer_ipi,customer_address,
            price,price_words,file_type,
            term_start,term_end,term_years,publishing_rights,publishing_shares,royalty,
            samples,state_country,country,credit,rendered_text,
            accepted_at,template_version,text_hash,folio,template_file)
            VALUES(:preset_id,:contract_date,:beat_title,:producer_alias,:owner_fullname,
            :producer_ipi,:customer_fullname,:customer_alias,:customer_ipi,:customer_address,
            :price,:price_words,:file_type,
            :term_start,:term_end,:term_years,:publishing_rights,:publishing_shares,:royalty,
            :samples,:state_country,:country,:credit,:rendered_text,
            :accepted_at,:template_version,:text_hash,:folio,:template_file)""",
            sale,
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def list_sales(db_path: Path, limit: int = HISTORY_LIMIT) -> list[dict]:
    con = get_connection(db_path)
    try:
        init_db(con)
        cur = con.execute("SELECT id,folio,contract_date,beat_title,customer_alias,price,template_version,created_at FROM sales ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        con.close()


def get_sale(db_path: Path, sale_id: int) -> dict | None:
    con = get_connection(db_path)
    try:
        init_db(con)
        cur = con.execute("SELECT * FROM sales WHERE id=?", (sale_id,))
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def delete_sale(db_path: Path, sale_id: int) -> bool:
    """Delete a history record. Folio numbers are never reused (counter keeps going)."""
    con = get_connection(db_path)
    try:
        init_db(con)
        cur = con.execute("DELETE FROM sales WHERE id=?", (sale_id,))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


ALLOWED_PRESET_FIELDS = {"name", "kind", "term_years",
                         "file_type", "royalty", "publishing_shares", "template_file",
                         "distribute_copies", "audio_streams"}


_PRESET_DEFAULTS = {
    "name": "Untitled Tier",
    "kind": "non-exclusive",
    "term_years": DEFAULT_TERM_YEARS,
    "file_type": "MP3",
    "royalty": "0%",
    "publishing_shares": "Producer retains 100%",
    "template_file": NON_EXCLUSIVE_TEMPLATE,
    "distribute_copies": DEFAULT_DISTRIBUTE_COPIES,
    "audio_streams": DEFAULT_AUDIO_STREAMS,
}


def create_preset(db_path: Path, preset: dict) -> int:
    # FIX: preset.get(k, default) kept explicit None (NOT NULL violation with a
    # raw sqlite error). Empty/None now falls back to tier defaults, and a
    # duplicate name raises ValueError (friendly for the UI) instead of a raw
    # IntegrityError traceback.
    import sqlite3
    con = get_connection(db_path)
    try:
        init_db(con)
        row = {}
        for k in ("name", "kind", "term_years", "file_type",
                  "royalty", "publishing_shares", "template_file",
                  "distribute_copies", "audio_streams"):
            v = preset.get(k)
            if v is None or (isinstance(v, str) and not v.strip()):
                v = _PRESET_DEFAULTS[k]
            row[k] = v
        try:
            cur = con.execute(
                """INSERT INTO presets(name,kind,term_years,file_type,
                royalty,publishing_shares,template_file,distribute_copies,audio_streams)
                VALUES(:name,:kind,:term_years,:file_type,
                :royalty,:publishing_shares,:template_file,:distribute_copies,:audio_streams)""",
                row,
            )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"preset name already exists: {row.get('name')!r}") from e
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def update_preset(db_path: Path, preset_id: int, patch: dict) -> bool:
    import sqlite3
    fields = {k: v for k, v in patch.items() if k in ALLOWED_PRESET_FIELDS}
    if not fields:
        return False
    con = get_connection(db_path)
    try:
        init_db(con)
        cols = ", ".join(f"{k}=:{k}" for k in fields)
        fields["id"] = preset_id
        try:
            cur = con.execute(f"UPDATE presets SET {cols} WHERE id=:id", fields)
        except sqlite3.IntegrityError as e:
            raise ValueError("preset name already exists") from e
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def delete_preset(db_path: Path, preset_id: int) -> bool:
    """Delete a tier. Returns False when missing OR still referenced by saved sales."""
    import sqlite3
    con = get_connection(db_path)
    try:
        init_db(con)
        try:
            cur = con.execute("DELETE FROM presets WHERE id=?", (preset_id,))
        except sqlite3.IntegrityError:
            # FK: preset used by sales history (WORM) — never cascade
            return False
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()
