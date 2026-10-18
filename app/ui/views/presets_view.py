"""Presets view: commercial tiers (offer) — duplicate / edit / delete + assign contract."""
from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from ...database.repositories import (
    create_preset, delete_preset, get_preset, list_presets, update_preset,
)
from ...engine.policy import (
    DEFAULT_AUDIO_STREAMS,
    DEFAULT_DISTRIBUTE_COPIES,
    TIER_NAME_MAX_LEN,
)
from ...services import template_service as tpls
from ...utils.paths import db_path
from ..constants import TERM_MIN_YEARS, TERM_MAX_YEARS


class PresetsView(QWidget):
    changed = Signal()  # emit after dup/save/delete so Generator refreshes its combo

    def __init__(self, on_status=None, parent=None):
        super().__init__(parent)
        self._on_status = on_status or (lambda msg: None)
        lay = QVBoxLayout(self)
        self.role_hint = QLabel(
            "Commercial tiers (the offer): deliverables, term, royalty, publishing "
            "+ which contract text each tier uses.")
        self.role_hint.setWordWrap(True)
        lay.addWidget(self.role_hint)
        self.list = QListWidget()
        self.list.itemClicked.connect(self.open_item)
        lay.addWidget(self.list)

        form = QFormLayout()
        self.p_name = QLineEdit()
        self.p_file = QLineEdit()
        self.p_royalty = QLineEdit()
        self.p_publishing = QLineEdit()
        self.p_term = QLineEdit()
        self.p_term.setValidator(QIntValidator(TERM_MIN_YEARS, TERM_MAX_YEARS, self))
        self.p_copies = QLineEdit()
        self.p_copies.setPlaceholderText("number or unlimited")
        self.p_streams = QLineEdit()
        self.p_streams.setPlaceholderText("number or unlimited")
        self.p_template = QComboBox()
        form.addRow("Name", self.p_name)
        form.addRow("File type", self.p_file)
        form.addRow("Royalty", self.p_royalty)
        form.addRow("Publishing", self.p_publishing)
        form.addRow("Term (years)", self.p_term)
        form.addRow("Copies", self.p_copies)
        form.addRow("Streams", self.p_streams)
        form.addRow("Template", self.p_template)
        lay.addLayout(form)

        row = QHBoxLayout()
        self.btn_dup = QPushButton("Duplicate as new")
        self.btn_dup.clicked.connect(self.duplicate)
        self.btn_dup_tpl = QPushButton("Duplicate + template")
        self.btn_dup_tpl.setToolTip("Duplicate the tier AND its contract text as a new template")
        self.btn_dup_tpl.clicked.connect(self.duplicate_with_template)
        self.btn_save = QPushButton("Save changes")
        self.btn_save.clicked.connect(self.save_changes)
        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(self.delete)
        for b in (self.btn_dup, self.btn_dup_tpl, self.btn_save, self.btn_del):
            row.addWidget(b)
        lay.addLayout(row)
        self.reload_template_options()
        self.reload()

    def reload_template_options(self):
        """Refresh template combo (called when the library changes). Keeps selection."""
        current = self.p_template.currentData()
        self.p_template.clear()
        for t in tpls.list_templates():
            self.p_template.addItem(f"{t['name']} [{t['source']}]", t["name"])
        if current:
            idx = self.p_template.findData(current)
            if idx >= 0:
                self.p_template.setCurrentIndex(idx)
            else:
                # FIX: orphan template (file deleted externally) — keep the
                # value visible as [missing] instead of silently switching to
                # another template and saving the wrong contract text.
                self.p_template.addItem(f"{current} [missing]", current)
                self.p_template.setCurrentIndex(self.p_template.count() - 1)
                self._on_status(
                    f"Template {current} not found — reassign before saving.")

    def reload(self):
        self.list.clear()
        for p in list_presets(db_path()):
            self.list.addItem(f"#{p['id']} {p['name']} [{p['kind']}]")

    def selected_id(self) -> int | None:
        it = self.list.currentItem()
        if not it:
            return None
        return int(it.text().split()[0].lstrip("#"))

    def open_item(self, _item=None):
        pid = self.selected_id()
        p = get_preset(db_path(), pid) if pid else None
        if not p:
            return
        self.p_name.setText(p["name"])
        self.p_file.setText(p["file_type"])
        self.p_royalty.setText(p["royalty"])
        self.p_publishing.setText(p["publishing_shares"])
        self.p_term.setText(str(p["term_years"]))
        self.p_copies.setText(p.get("distribute_copies", "") or "")
        self.p_streams.setText(p.get("audio_streams", "") or "")
        idx = self.p_template.findData(p["template_file"])
        if idx >= 0:
            self.p_template.setCurrentIndex(idx)

    @staticmethod
    def _years_or(text: str, fallback) -> int:
        """Parse or fallback, clamped to the term policy (validators don't enforce)."""
        try:
            return max(TERM_MIN_YEARS, min(TERM_MAX_YEARS, int(text.strip())))
        except (ValueError, AttributeError):
            return fallback

    def duplicate(self):
        pid = self.selected_id()
        if not pid:
            return
        p = get_preset(db_path(), pid)
        try:
            new_id = create_preset(db_path(), {
                "name": (self.p_name.text().strip() or p["name"] + " Copy")[:TIER_NAME_MAX_LEN],
                "kind": p["kind"],
                "term_years": self._years_or(self.p_term.text(), p["term_years"]),
                "file_type": self.p_file.text().strip() or p["file_type"],
                "royalty": self.p_royalty.text().strip() or p["royalty"],
                "publishing_shares": self.p_publishing.text().strip() or p["publishing_shares"],
                "template_file": self.p_template.currentData() or p["template_file"],
                "distribute_copies": self.p_copies.text().strip() or p.get("distribute_copies", DEFAULT_DISTRIBUTE_COPIES),
                "audio_streams": self.p_streams.text().strip() or p.get("audio_streams", DEFAULT_AUDIO_STREAMS),
            })
        except ValueError as e:
            QMessageBox.warning(self, "Duplicate tier", str(e))
            return
        self._on_status(f"Preset duplicated #{new_id}")
        self.reload()
        self.changed.emit()

    def duplicate_with_template(self):
        """Duplicate the tier AND its contract text in one step (anti-friction bridge).

        New tier points to a new user template copied from the source content,
        so editing the contract never touches the original tier's text.
        """
        pid = self.selected_id()
        if not pid:
            return
        p = get_preset(db_path(), pid)
        if not p:
            return
        name, ok = QInputDialog.getText(
            self, "Duplicate tier + template", "New tier name:",
            text=f"{p['name']} Copy")
        if not ok:
            return
        new_name = (name.strip() or f"{p['name']} Copy")[:TIER_NAME_MAX_LEN]
        try:
            content = tpls.read_template(p["template_file"])
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "Duplicate tier + template", str(e))
            return
        stem = p["template_file"][:-3] if p["template_file"].lower().endswith(".md") else p["template_file"]
        candidate = f"{stem}_copy.md"
        n = 2
        while tpls.template_exists(candidate):
            candidate = f"{stem}_copy{n}.md"
            n += 1
        tpls.write_template(candidate, content)
        try:
            new_id = create_preset(db_path(), {
                "name": new_name,
                "kind": p["kind"],
                "term_years": self._years_or(self.p_term.text(), p["term_years"]),
                "file_type": self.p_file.text().strip() or p["file_type"],
                "royalty": self.p_royalty.text().strip() or p["royalty"],
                "publishing_shares": self.p_publishing.text().strip() or p["publishing_shares"],
            "template_file": candidate,
            "distribute_copies": self.p_copies.text().strip() or p.get("distribute_copies", DEFAULT_DISTRIBUTE_COPIES),
            "audio_streams": self.p_streams.text().strip() or p.get("audio_streams", DEFAULT_AUDIO_STREAMS),
        })
        except ValueError as e:
            QMessageBox.warning(self, "Duplicate tier + template", str(e))
            return
        self.reload_template_options()
        self.reload()
        for i in range(self.list.count()):
            if self.list.item(i).text().startswith(f"#{new_id} "):
                self.list.setCurrentRow(i)
                break
        self.open_item(None)
        self._on_status(f"Tier #{new_id} '{new_name}' + template {candidate} created")
        self.changed.emit()

    def save_changes(self):
        pid = self.selected_id()
        if not pid:
            return
        patch = {}
        if self.p_name.text().strip():
            patch["name"] = self.p_name.text().strip()[:TIER_NAME_MAX_LEN]
        if self.p_file.text().strip():
            patch["file_type"] = self.p_file.text().strip()
        if self.p_royalty.text().strip():
            patch["royalty"] = self.p_royalty.text().strip()
        if self.p_publishing.text().strip():
            patch["publishing_shares"] = self.p_publishing.text().strip()
        if self.p_term.text().strip():
            try:
                patch["term_years"] = max(TERM_MIN_YEARS,
                                          min(TERM_MAX_YEARS, int(self.p_term.text().strip())))
            except ValueError:
                pass
        if self.p_template.currentData():
            chosen = self.p_template.currentData()
            if " [missing]" in self.p_template.currentText() or not tpls.template_exists(chosen):
                self._on_status(f"Template {chosen} is missing — pick an existing one.")
                return
            patch["template_file"] = chosen
        if self.p_copies.text().strip():
            patch["distribute_copies"] = self.p_copies.text().strip()
        if self.p_streams.text().strip():
            patch["audio_streams"] = self.p_streams.text().strip()
        try:
            ok = update_preset(db_path(), pid, patch)
        except ValueError as e:
            QMessageBox.warning(self, "Save tier", str(e))
            return
        self._on_status(f"Preset #{pid} updated" if ok else "No changes")
        self.reload()
        self.changed.emit()

    def delete(self):
        pid = self.selected_id()
        if not pid:
            return
        if delete_preset(db_path(), pid):
            self._on_status(f"Preset #{pid} deleted")
            self.reload()
            self.changed.emit()
        else:
            self._on_status(f"Preset #{pid} is used by saved sales — cannot delete")
