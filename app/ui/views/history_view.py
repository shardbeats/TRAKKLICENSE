"""History view: past sales list (WORM — records deletable, never editable)."""
from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QMessageBox, QPushButton, QTextBrowser,
    QVBoxLayout, QWidget,
)

from ...database.repositories import delete_sale, get_sale, list_sales
from ...engine.policy import LONG_DOC_NOTICE_CHARS
from ...services.generation import template_version
from ...utils.paths import db_path


class HistoryView(QWidget):
    def __init__(self, on_notice: Callable[[str], None] | None = None, parent=None):
        super().__init__(parent)
        self._on_notice = on_notice or (lambda msg: None)
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.btn_reload = QPushButton("Reload history")
        self.btn_reload.clicked.connect(self.reload)
        self.btn_delete = QPushButton("Delete selected")
        self.btn_delete.clicked.connect(self.delete_selected)
        row.addWidget(self.btn_reload)
        row.addWidget(self.btn_delete)
        self.list = QListWidget()
        self.view = QTextBrowser()
        self.list.itemClicked.connect(self.open_item)
        lay.addLayout(row)
        lay.addWidget(self.list)
        lay.addWidget(self.view)

    def reload(self):
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        self.list.clear()
        for s in list_sales(db_path()):
            tag = f" [{s['folio']}]" if s.get("folio") else ""
            item = QListWidgetItem(
                f"#{s['id']}{tag} {s['contract_date']} — {s['beat_title']} "
                f"→ {s['customer_alias']} ({s['price']})")
            # FIX: store the id in UserRole so parsing never depends on the
            # display format (folios/titles with "#" or spaces broke _id_of).
            item.setData(Qt.UserRole, int(s["id"]))
            self.list.addItem(item)

    @staticmethod
    def _id_of(item) -> int:
        import re
        try:
            stored = item.data(256)  # Qt.UserRole
            if stored is not None:
                return int(stored)
        except Exception:
            pass
        m = re.match(r"\s*#(\d+)", item.text() or "")
        if not m:
            raise ValueError(f"cannot parse sale id from {item.text()!r}")
        return int(m.group(1))

    def open_item(self, item):
        sid = self._id_of(item)
        s = get_sale(db_path(), sid)
        if s:
            # FIX: no silent [:20000] truncation — show the full sold text.
            # A notice is appended when the document is very long.
            full = s["rendered_text"] or ""
            self.view.setMarkdown(full)
            if len(full) > LONG_DOC_NOTICE_CHARS:
                self._on_notice(
                    f"NOTE sale #{sid}: display shows full text "
                    f"({len(full)} chars) — scroll to review.")
            cur = template_version(s.get("template_file", "")) if s.get("template_file") else ""
            if cur and s.get("template_version") and cur != s["template_version"]:
                self._on_notice(
                    f"NOTE sale #{sid}: template {s.get('template_file')} changed "
                    f"(sold v{s.get('template_version')}, now v{cur}) — "
                    "re-generate as new sale, never edit.")

    def delete_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        sid = self._id_of(item)
        if QMessageBox.question(self, "Delete sale",
                                f"Delete sale #{sid} from history? This cannot be undone.",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        if delete_sale(db_path(), sid):
            self._on_notice(f"Sale #{sid} deleted")
            self.view.clear()
            self.reload()
