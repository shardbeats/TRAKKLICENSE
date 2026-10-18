import sqlite3
from app.database.seed import ensure_seed
from app.database import repositories as repo


def test_migrate_legacy_price_columns(tmp_path):
    db = tmp_path / "legacy.db"
    con = sqlite3.connect(str(db))
    con.execute("""CREATE TABLE presets(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
      kind TEXT NOT NULL, price REAL NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
      term_years INTEGER NOT NULL DEFAULT 5, file_type TEXT NOT NULL DEFAULT 'MP3',
      royalty TEXT NOT NULL DEFAULT '0%', publishing_shares TEXT NOT NULL DEFAULT 'P',
      template_file TEXT NOT NULL DEFAULT 'non_exclusive_lease.md')""")
    con.execute("INSERT INTO presets(name,kind,price,currency,term_years) VALUES('Old', 'non-exclusive', 29.0, 'USD', 5)")
    con.commit()
    con.close()
    ensure_seed(db)
    presets = {p["name"]: p for p in repo.list_presets(db)}
    assert "Old" in presets
    assert "price" not in presets["Old"]
    assert len(presets) == 6  # 1 legacy + 5 seed
