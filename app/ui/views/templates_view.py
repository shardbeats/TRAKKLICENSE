"""Templates library view: contract texts ({VARS} + markdown)."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from ...database.repositories import list_presets
from ...services import document_service as docs
from ...services import template_service as tpls
from ...utils.paths import db_path
from ..dialogs.template_editor import TemplateEditor


class TemplatesView(QWidget):
    changed = Signal()  # library or content changed → refresh combos + preview

    def __init__(self, on_status=None, preview_fn=None, parent=None):
        super().__init__(parent)
        self._on_status = on_status or (lambda msg: None)
        self._preview_fn = preview_fn or (lambda text: {"rendered": text})
        lay = QVBoxLayout(self)
        self.role_hint = QLabel(
            "Contract texts: the legal wording with {VARIABLES}. Tiers (Presets) "
            "decide which text each offer uses. Edits apply to future sales — "
            "history keeps every sold version.")
        self.role_hint.setWordWrap(True)
        lay.addWidget(self.role_hint)
        self.list = QListWidget()
        lay.addWidget(self.list)

        row = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_new.clicked.connect(self.create)
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self.edit)
        self.btn_dup = QPushButton("Duplicate")
        self.btn_dup.clicked.connect(self.duplicate)
        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(self.delete)
        self.btn_reset = QPushButton("Reset to bundled")
        self.btn_reset.clicked.connect(self.reset)
        self.btn_folder = QPushButton("Open folder")
        self.btn_folder.clicked.connect(lambda: docs.open_file(tpls.user_templates_dir()))
        for b in (self.btn_new, self.btn_edit, self.btn_dup,
                  self.btn_del, self.btn_reset, self.btn_folder):
            row.addWidget(b)
        lay.addLayout(row)
        self.reload()

    def reload(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        current = self.selected_name()
        self.list.clear()
        for t in tpls.list_templates():
            item = QListWidgetItem(f"{t['name']} [{t['source']}]")
            # FIX: names may contain " [" — never parse the label, use UserRole.
            item.setData(Qt.UserRole, t["name"])
            self.list.addItem(item)
        if current:
            for i in range(self.list.count()):
                if self.list.item(i).data(256) == current:
                    self.list.setCurrentRow(i)
                    break

    def selected_name(self) -> str | None:
        it = self.list.currentItem()
        if not it:
            return None
        try:
            stored = it.data(256)  # Qt.UserRole
            if stored:
                return str(stored)
        except Exception:
            pass
        return it.text().rsplit(" [", 1)[0]

    def _source_of(self, name: str) -> str:
        for t in tpls.list_templates():
            if t["name"] == name:
                return t["source"]
        return ""

    def _open_editor(self, name: str, initial: str):
        def _preview(text: str) -> dict:
            return self._preview_fn(text)

        def _save(fname: str, text: str):
            tpls.write_template(fname, text)
            self._on_status(f"Template {fname} saved")
            self.reload()
            self.changed.emit()

        def _reset(fname: str):
            tpls.reset_template(fname)
            self._on_status(f"Template {fname} reset to bundled")
            self.reload()
            self.changed.emit()

        dlg = TemplateEditor(self, name, initial,
                             self._source_of(name) == "override",
                             _preview, _save, _reset)
        dlg.exec()

    def create(self):
        name, ok = QInputDialog.getText(self, "New template", "Filename (e.g. my_lease.md):")
        if not ok:
            return
        try:
            clean = tpls.sanitize_name(name)
        except ValueError as e:
            QMessageBox.warning(self, "New template", str(e))
            return
        if tpls.template_exists(clean):
            QMessageBox.warning(self, "New template", f"{clean} already exists — use Duplicate.")
            return
        self._open_editor(clean, "")

    def edit(self):
        name = self.selected_name()
        if not name:
            return
        try:
            self._open_editor(name, tpls.read_template(name))
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "Edit template", str(e))

    def duplicate(self):
        name = self.selected_name()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Duplicate template", "New filename:")
        if not ok:
            return
        try:
            clean = tpls.sanitize_name(new)
            content = tpls.read_template(name)
        except (ValueError, FileNotFoundError) as e:
            QMessageBox.warning(self, "Duplicate template", str(e))
            return
        if tpls.template_exists(clean):
            QMessageBox.warning(self, "Duplicate template", f"{clean} already exists.")
            return
        tpls.write_template(clean, content)
        self._on_status(f"Template duplicated as {clean}")
        self.reload()
        self.changed.emit()

    def _used_by(self, name: str) -> list[str]:
        return [p["name"] for p in list_presets(db_path())
                if p.get("template_file") == name]

    def delete(self):
        name = self.selected_name()
        if not name:
            return
        if (tpls.user_templates_dir() / name).is_file() is False:
            self._on_status(f"{name} is bundled — nothing to delete (Reset applies to overrides)")
            return
        if self._source_of(name) == "override":
            self._on_status(f"{name} overrides a seed — use Reset to bundled, not Delete")
            return
        used = self._used_by(name)
        if used:
            self._on_status(f"{name} is used by preset(s) {', '.join(used)} — reassign first")
            return
        if QMessageBox.question(self, "Delete template",
                                f"Delete custom template {name}?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        tpls.delete_template(name)
        self._on_status(f"Template {name} deleted")
        self.reload()
        self.changed.emit()

    def reset(self):
        name = self.selected_name()
        if not name:
            return
        if self._source_of(name) != "override":
            self._on_status(f"{name} has no bundled version to reset to")
            return
        if QMessageBox.question(self, "Reset template",
                                f"Discard your changes to {name} and restore the bundled version?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        tpls.reset_template(name)
        self._on_status(f"Template {name} reset to bundled")
        self.reload()
        self.changed.emit()
