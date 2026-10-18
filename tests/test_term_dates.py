"""Term dates: start = today, end = start + preset years (auto, read-only)."""
import datetime
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRAKKLICENSE_SKIP_GUI") == "1", reason="gui skip"
)

try:
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="PySide6 missing")


def test_compute_term_end_basic():
    from app.services.generation import compute_term_end
    assert compute_term_end("2026-10-18", 5) == "2031-10-18"
    assert compute_term_end("2026-10-18", "10") == "2036-10-18"
    assert compute_term_end("2024-02-29", 1) == "2025-02-28"  # leap → Feb 28
    assert compute_term_end("not-a-date", 5) == ""
    assert compute_term_end("2026-10-18", "") == ""
    assert compute_term_end("", 5) == ""
    assert compute_term_end("2026-10-18", 0) == ""
    assert compute_term_end("2026-10-18", -3) == ""
    assert compute_term_end("2026-10-18", 99999) == ""  # overflow, no crash


def test_build_render_data_autofills_blank_end():
    from app.services.generation import build_render_data
    d = build_render_data({"TERM_START": "2026-10-18", "TERM_END": "",
                           "TERM_YEARS": "5"})
    assert d["TERM_END"] == "2031-10-18"
    # explicit end respected, never overwritten
    d2 = build_render_data({"TERM_START": "2026-10-18", "TERM_END": "2030-01-01",
                            "TERM_YEARS": "5"})
    assert d2["TERM_END"] == "2030-01-01"


@needs_qt
def test_gui_term_start_today_end_auto(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        today = datetime.date.today().isoformat()
        assert "TERM_START" not in w.inputs  # derived, not typed
        assert w.inputs["CONTRACT_DATE"].text() == today
        assert w.inputs["TERM_END"].isReadOnly()
        # start derived from effective date in render data
        w.on_generate()
        assert w._last_data["TERM_START"] == today
        # end = today + current preset years
        from app.services.generation import compute_term_end
        years = w.current_preset()["term_years"]
        assert w.inputs["TERM_END"].text() == compute_term_end(today, years)
        # backdating the effective date shifts start + end
        w.inputs["CONTRACT_DATE"].setText("2025-01-15")
        assert w.inputs["TERM_END"].text() == compute_term_end("2025-01-15", years)
        w.on_generate()
        assert w._last_data["TERM_START"] == "2025-01-15"
        # switching preset (different years) recomputes end
        ids = [w.preset_cb.itemData(i) for i in range(w.preset_cb.count())]
        assert len(ids) >= 2
        other = next(pid for pid in ids if pid != w.preset_cb.currentData())
        w.preset_cb.setCurrentIndex(w.preset_cb.findData(other))
        new_years = w.current_preset()["term_years"]
        assert w.inputs["TERM_END"].text() == compute_term_end("2025-01-15", new_years)
    finally:
        w.close()


def test_seeds_default_10y_and_plain_names(tmp_path):
    from app.database.seed import ensure_seed
    from app.database.repositories import list_presets
    db = tmp_path / "s.db"
    ensure_seed(db)
    presets = {p["name"]: p for p in list_presets(db)}
    assert set(presets) == {"MP3 Lease", "WAV Lease", "Trackout Lease",
                            "Unlimited Lease", "Exclusive"}
    assert {p["term_years"] for p in presets.values()} == {10}


def test_legacy_migration_rename_terms_and_fk(tmp_path):
    """Legacy DB: 10Y renamed (id kept, sales intact), pristine 5→10, edits untouched."""
    from app.database.connection import init_db, get_connection
    from app.database.seed import ensure_seed
    from app.database.repositories import list_presets
    db = tmp_path / "legacy.db"
    con = get_connection(db)
    init_db(con)
    excl_id = con.execute(
        "INSERT INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file)"
        "VALUES('Exclusive 10Y','exclusive',10,'WAV + stems + instrumental','3%',"
        "'Licensor 50% / Licensee 50%','exclusive_10y.md')").lastrowid
    con.execute(
        "INSERT INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file)"
        "VALUES('MP3 Lease','non-exclusive',5,'Tagged MP3 + Untagged MP3','0%',"
        "'Producer retains 100%','non_exclusive_lease.md')")
    con.execute(
        "INSERT INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file)"
        "VALUES('WAV Lease','non-exclusive',5,'MY CUSTOM FILES','0%',"
        "'Producer retains 100%','non_exclusive_lease.md')")
    con.commit()
    con.close()
    ensure_seed(db)
    presets = {p["name"]: p for p in list_presets(db)}
    assert "Exclusive 10Y" not in presets and "Exclusive" in presets
    assert presets["Exclusive"]["id"] == excl_id  # rename keeps id → sales FK intact
    assert presets["MP3 Lease"]["term_years"] == 10  # pristine migrated
    edited = presets["WAV Lease"]
    assert edited["term_years"] == 5 and edited["file_type"] == "MY CUSTOM FILES"  # untouched


def test_rename_skipped_on_name_clash(tmp_path):
    from app.database.seed import ensure_seed
    from app.database.repositories import create_preset, list_presets
    db = tmp_path / "clash.db"
    ensure_seed(db)
    create_preset(db, {"name": "Exclusive 10Y", "kind": "exclusive", "term_years": 7,
                       "file_type": "X", "royalty": "9%",
                       "publishing_shares": "y", "template_file": "exclusive_10y.md"})
    ensure_seed(db)  # rename blocked: user's "Exclusive" wins, legacy row kept
    names = [p["name"] for p in list_presets(db)]
    assert "Exclusive 10Y" in names and names.count("Exclusive") == 1


@needs_qt
def test_exclusive_caps_unlimited_in_form(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        excl = next(i for i in range(w.preset_cb.count())
                    if w.preset_cb.itemText(i).startswith("Exclusive"))
        w.preset_cb.setCurrentIndex(excl)
        assert w.inputs["DISTRIBUTE_COPIES"].text() == "unlimited"
        assert w.inputs["AUDIO_STREAMS"].text() == "unlimited"
        w.on_generate()
        assert w._last_data["DISTRIBUTE_COPIES_WORD"] == "unlimited"
        assert w._last_data["AUDIO_STREAMS_WORD"] == "unlimited"
        wav = next(i for i in range(w.preset_cb.count())
                   if w.preset_cb.itemText(i).startswith("WAV Lease"))
        w.preset_cb.setCurrentIndex(wav)
        assert w.inputs["DISTRIBUTE_COPIES"].text() == "5000"
        assert w.inputs["AUDIO_STREAMS"].text() == "500000"
    finally:
        w.close()


@needs_qt
def test_tier_switch_fills_form_and_years_editable(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    from app.services.generation import compute_term_end
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        idx = next(i for i in range(w.preset_cb.count())
                   if w.preset_cb.itemText(i).startswith("WAV Lease"))
        w.preset_cb.setCurrentIndex(idx)
        assert w.inputs["FILE_TYPE"].text() == "Tagged MP3 + Untagged MP3 + Untagged WAV"
        assert w.inputs["ROYALTY_AMOUNT"].text() == "0%"
        assert w.inputs["TERM_YEARS"].text() == "10"
        # user overrides the term → end follows
        w.inputs["TERM_YEARS"].setText("3")
        start = w.inputs["CONTRACT_DATE"].text()
        assert w.inputs["TERM_END"].text() == compute_term_end(start, 3)
        w.on_generate()
        assert "3 years from" in w._last_text
        # tier preset itself editable (Presets view term field)
        row = next(i for i in range(w.presets.list.count())
                   if "WAV Lease" in w.presets.list.item(i).text())
        w.presets.list.setCurrentRow(row)
        pid = w.presets.selected_id()
        w.presets.open_item(None)
        assert w.presets.p_term.text() == "10"
        w.presets.p_term.setText("7")
        w.presets.save_changes()
        from app.database.repositories import get_preset
        from app.utils.paths import db_path
        assert get_preset(db_path(), pid)["term_years"] == 7
    finally:
        w.close()


def test_exclusive_files_migration(tmp_path):
    """Pristine 'WAV + stems + instrumental' → 'WAV + stems'; edited rows kept."""
    from app.database.connection import init_db, get_connection
    from app.database.seed import ensure_seed
    from app.database.repositories import list_presets
    db = tmp_path / "files.db"
    con = get_connection(db)
    init_db(con)
    con.execute(
        "INSERT INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file)"
        "VALUES('Exclusive','exclusive',10,'WAV + stems + instrumental','3%',"
        "'Licensor 50% / Licensee 50%','exclusive_10y.md')")
    con.execute(
        "INSERT INTO presets(name,kind,term_years,file_type,royalty,publishing_shares,template_file)"
        "VALUES('Exclusive Custom','exclusive',10,'WAV + stems + instrumental','5%',"
        "'Licensor 50% / Licensee 50%','exclusive_10y.md')")
    con.commit()
    con.close()
    ensure_seed(db)
    presets = {p["name"]: p for p in list_presets(db)}
    assert presets["Exclusive"]["file_type"] == "WAV + stems"
    edited = presets["Exclusive Custom"]
    assert edited["file_type"] == "WAV + stems + instrumental"  # royalty differs → untouched


def test_exclusive_caps_unlimited_and_migrated(tmp_path):
    """Exclusive tier: unlimited caps in seed, backfilled on legacy DBs,
    user-customized caps never clobbered."""
    import sqlite3
    from app.database.seed import ensure_seed
    from app.database.repositories import list_presets, update_preset
    db = tmp_path / "caps.db"
    ensure_seed(db)
    presets = {p["name"]: p for p in list_presets(db)}
    assert presets["Exclusive"]["distribute_copies"] == "unlimited"
    assert presets["Exclusive"]["audio_streams"] == "unlimited"
    assert presets["WAV Lease"]["distribute_copies"] == "5000"
    # legacy schema without caps columns → columns added, exclusive backfilled
    legacy = tmp_path / "legacy_caps.db"
    con = sqlite3.connect(str(legacy))
    con.execute("""CREATE TABLE presets(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
      kind TEXT NOT NULL, term_years INTEGER NOT NULL DEFAULT 10,
      file_type TEXT NOT NULL DEFAULT 'MP3', royalty TEXT NOT NULL DEFAULT '0%',
      publishing_shares TEXT NOT NULL DEFAULT 'P',
      template_file TEXT NOT NULL DEFAULT 'non_exclusive_lease.md')""")
    con.execute("INSERT INTO presets(name,kind) VALUES('Exclusive','exclusive')")
    con.execute("INSERT INTO presets(name,kind) VALUES('WAV Lease','non-exclusive')")
    con.commit()
    con.close()
    ensure_seed(legacy)
    after = {p["name"]: p for p in list_presets(legacy)}
    assert after["Exclusive"]["distribute_copies"] == "unlimited"
    assert after["Exclusive"]["audio_streams"] == "unlimited"
    assert after["WAV Lease"]["distribute_copies"] == "5000"
    # customized caps survive re-seed
    update_preset(legacy, after["Exclusive"]["id"],
                  {"distribute_copies": "100000", "audio_streams": "200000"})
    ensure_seed(legacy)
    custom = {p["name"]: p for p in list_presets(legacy)}
    assert custom["Exclusive"]["distribute_copies"] == "100000"
    assert custom["Exclusive"]["audio_streams"] == "200000"


@needs_qt
def test_term_years_clamped_to_policy(tmp_path, monkeypatch):
    """QIntValidator doesn't enforce: 999 must normalize to 100 everywhere."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    from app.services.generation import compute_term_end
    from app.database.repositories import get_preset
    from app.utils.paths import db_path
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        start = w.inputs["CONTRACT_DATE"].text()
        w.inputs["TERM_YEARS"].setText("999")
        assert w.inputs["TERM_YEARS"].text() == "100"
        assert w.inputs["TERM_END"].text() == compute_term_end(start, 100)
        w.inputs["TERM_YEARS"].setText("0")
        assert w.inputs["TERM_YEARS"].text() == "1"
        # tier save path clamps too
        row = next(i for i in range(w.presets.list.count())
                   if "WAV Lease" in w.presets.list.item(i).text())
        w.presets.list.setCurrentRow(row)
        pid = w.presets.selected_id()
        w.presets.open_item(None)
        w.presets.p_term.setText("999")
        w.presets.save_changes()
        assert get_preset(db_path(), pid)["term_years"] == 100
    finally:
        w.close()
