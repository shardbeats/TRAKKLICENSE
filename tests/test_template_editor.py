"""Template editor GUI: guide insert, preview with sale data, warn-and-save, presets assign."""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TRAKKLICENSE_SKIP_GUI") == "1", reason="gui skip"
)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
    HAS_QT = True
except ImportError:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="PySide6 missing")


@needs_qt
def test_editor_guide_insert_and_preview(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w.tabs.count() == 4
        assert len(w._view_actions) == 4
        # open editor for a bundled seed (copy-on-write on save)
        from app.services import template_service as tpls
        from app.ui.dialogs.template_editor import TemplateEditor
        saved = {}

        def _preview(text):
            return w.preview_template_text(text)

        dlg = TemplateEditor(w, "non_exclusive_lease.md", "Hi {PRODUCT_TITLE} {NOPE}",
                             False, _preview,
                             lambda f, t: saved.update({f: t}),
                             lambda f: None)
        try:
            # guide lists every variable with description
            assert dlg.guide.count() >= 25
            # filter narrows (TRACK_TITLE aliases PRODUCT_TITLE, so use a unique key)
            dlg.filter.setText("PRODUCT_PRICE_WORD")
            visible = [dlg.guide.item(i).text() for i in range(dlg.guide.count())
                       if not dlg.guide.isRowHidden(i)]
            assert len(visible) == 1 and "PRODUCT_PRICE_WORD" in visible[0]
            dlg.filter.setText("")
            # validation flags unknown
            assert "NOPE" in dlg.validation.text()
            # insert at cursor appends the variable
            from PySide6.QtGui import QTextCursor
            dlg.editor.moveCursor(QTextCursor.End)
            for i in range(dlg.guide.count()):
                if dlg.guide.item(i).data(Qt.UserRole) == "FOLIO":
                    dlg.guide.setCurrentRow(i)
                    break
            dlg.insert_selected()
            assert "{FOLIO}" in dlg.editor.toPlainText()
            # preview renders with current sale data
            dlg.tabs.setCurrentIndex(1)
            assert "Demo Beat" in dlg.preview.toPlainText()
            assert "NOPE" in dlg.preview_info.text()
            # save warns on unknown but saves on Yes (warn-and-save decision)
            monkeypatch.setattr(QMessageBox, "question",
                                staticmethod(lambda *a, **k: QMessageBox.Yes))
            dlg._do_save()
            assert saved["non_exclusive_lease.md"].count("{FOLIO}") == 1
            # bundled seed file untouched on disk (copy-on-write: nothing
            # written to the user dir, save went through the callback)
            assert "Hi {PRODUCT_TITLE} {NOPE}" not in tpls.read_template(
                "non_exclusive_lease.md")
            assert not (tpls.user_templates_dir() / "non_exclusive_lease.md").exists()
        finally:
            dlg.close()
    finally:
        w.close()


@needs_qt
def test_duplicate_tier_plus_template(tmp_path, monkeypatch):
    """One step: new tier + copied contract, linked; original untouched."""
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QInputDialog
    from app.ui.main_window import MainWindow
    from app.services import template_service as tpls
    from app.database.repositories import get_preset
    from app.utils.paths import db_path
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        w.presets.list.setCurrentRow(0)
        src_id = w.presets.selected_id()
        src = get_preset(db_path(), src_id)
        monkeypatch.setattr(QInputDialog, "getText",
                            staticmethod(lambda *a, **k: ("WAV Copy", True)))
        w.presets.duplicate_with_template()
        new_id = w.presets.selected_id()
        assert new_id != src_id
        new = get_preset(db_path(), new_id)
        assert new["name"] == "WAV Copy"
        assert new["kind"] == src["kind"] and new["term_years"] == src["term_years"]
        assert new["template_file"] != src["template_file"]
        assert new["template_file"].endswith("_copy.md")
        # copied content identical, source seed untouched, override is user-side
        assert tpls.read_template(new["template_file"]) == tpls.read_template(src["template_file"])
        from app.utils.paths import templates_dir
        assert (templates_dir() / new["template_file"]).exists() is False
        # generator combo + template combo picked up the newcomers
        assert w.preset_cb.findText(f"WAV Copy [{new['kind']}]") >= 0
        assert w.presets.p_template.findData(new["template_file"]) >= 0
        assert "WAV Copy" in w.generator.status.text()
    finally:
        w.close()


@needs_qt
def test_templates_view_crud_and_preset_assign(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAKKLICENSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QInputDialog
    from app.ui.main_window import MainWindow
    from app.services import template_service as tpls
    from app.database.repositories import list_presets
    from app.utils.paths import db_path
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        tpls.write_template("mine.md", "Custom {PRODUCT_TITLE}")
        w.templates.reload()
        w.templates.changed.emit()  # library changed → preset combos refresh
        assert any("mine.md" in w.templates.list.item(i).text()
                   for i in range(w.templates.list.count()))
        # preset can adopt the custom template
        w.presets.list.setCurrentRow(0)
        pid = w.presets.selected_id()
        w.presets.open_item(None)
        idx = w.presets.p_template.findData("mine.md")
        assert idx >= 0
        w.presets.p_template.setCurrentIndex(idx)
        w.presets.save_changes()
        from app.database.repositories import get_preset
        assert get_preset(db_path(), pid)["template_file"] == "mine.md"
        # generator renders through the custom template
        w.on_generate()
        assert w._last_text == "Custom Demo Beat"
        # in-use template cannot be deleted
        w.templates.list.setCurrentRow(
            next(i for i in range(w.templates.list.count())
                 if w.templates.list.item(i).text().startswith("mine.md")))
        monkeypatch.setattr(QMessageBox, "question",
                            staticmethod(lambda *a, **k: QMessageBox.Yes))
        w.templates.delete()
        assert tpls.template_exists("mine.md")  # still there
        assert "reassign first" in w.generator.status.text()
    finally:
        w.close()
