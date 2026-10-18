"""Template editor dialog: variables guide + markdown editor + live preview."""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from ...engine.variables import VARIABLES
from ...services.template_service import validate_template


class TemplateEditor(QDialog):
    """Modal editor. Caller provides file callbacks + a preview renderer.

    preview_fn(text) -> {"rendered": str, "missing": [...], "unknown": [...]}
    on_save(filename, text) / on_reset(filename) perform persistence.
    """

    def __init__(self, parent, filename, initial_text, can_reset,
                 preview_fn, on_save, on_reset):
        super().__init__(parent)
        self._filename = filename
        self._preview_fn = preview_fn
        self._on_save = on_save
        self._on_reset = on_reset
        self.setWindowTitle(f"Template — {filename}")
        self.resize(1000, 620)

        root = QVBoxLayout(self)
        split = QSplitter(Qt.Horizontal)

        # --- left: variables guide (BeatStars-style) ---
        guide = QWidget()
        gl = QVBoxLayout(guide)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.addWidget(QLabel("<b>Template variables guide</b>"))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter variables…")
        self.filter.textChanged.connect(self._apply_filter)
        gl.addWidget(self.filter)
        self.guide = QListWidget()
        for key in sorted(VARIABLES):
            item = QListWidgetItem(f"{{{key}}} = {VARIABLES[key]}")
            item.setData(Qt.UserRole, key)
            self.guide.addItem(item)
        self.guide.itemDoubleClicked.connect(lambda _it: self.insert_selected())
        gl.addWidget(self.guide)
        self.btn_insert = QPushButton("Insert at cursor")
        self.btn_insert.clicked.connect(self.insert_selected)
        gl.addWidget(self.btn_insert)

        # --- right: editor / preview tabs ---
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.editor = QPlainTextEdit()
        self.editor.setFont(mono)
        self.editor.setPlainText(initial_text)
        self.editor.textChanged.connect(self._refresh_validation)
        self.tabs.addTab(self.editor, "Markdown Editor")
        # preview page
        prev = QWidget()
        pl = QVBoxLayout(prev)
        pl.setContentsMargins(0, 0, 0, 0)
        self.preview_info = QLabel("")
        self.preview_info.setWordWrap(True)
        pl.addWidget(self.preview_info)
        self.preview = QTextBrowser()
        pl.addWidget(self.preview)
        self.tabs.addTab(prev, "Preview")
        self.tabs.currentChanged.connect(self._on_tab)
        rl.addWidget(self.tabs)
        self.validation = QLabel("")
        self.validation.setWordWrap(True)
        rl.addWidget(self.validation)

        split.addWidget(guide)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 5)
        root.addWidget(split)

        btns = QHBoxLayout()
        self.btn_reset = QPushButton("Reset template")
        self.btn_reset.setVisible(can_reset)
        self.btn_reset.clicked.connect(self._do_reset)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._do_save)
        btns.addStretch(1)
        btns.addWidget(self.btn_reset)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)
        root.addLayout(btns)

        self._refresh_validation()

    # -- guide --
    def _apply_filter(self, text: str):
        q = text.strip().lower()
        for i in range(self.guide.count()):
            it = self.guide.item(i)
            self.guide.setRowHidden(i, bool(q) and q not in it.text().lower())

    def insert_selected(self):
        item = self.guide.currentItem()
        if not item:
            return
        self.editor.insertPlainText(f"{{{item.data(Qt.UserRole)}}}")
        self.editor.setFocus()

    # -- validation + preview --
    def _validation_report(self) -> dict:
        return validate_template(self.editor.toPlainText())

    def _refresh_validation(self):
        rep = self._validation_report()
        parts = [f"{len(rep['used'])} variables"]
        if rep["unknown"]:
            parts.append("UNKNOWN (render literally): " + ", ".join(rep["unknown"]))
        if rep["unbalanced_if"]:
            parts.append(f"unbalanced {{IF}} ({rep['if_open']}) / {{ENDIF}} ({rep['if_close']})")
        self.validation.setText(" · ".join(parts) if len(parts) > 1
                                else f"OK — {parts[0]}, no unknown variables")

    def _on_tab(self, idx: int):
        if self.tabs.tabText(idx) != "Preview":
            return
        try:
            res = self._preview_fn(self.editor.toPlainText()) or {}
        except Exception as e:
            self.preview.setPlainText(f"Preview error: {e}")
            return
        self.preview.setMarkdown(res.get("rendered", "") or "")
        info = []
        if res.get("unknown"):
            info.append("unknown: " + ", ".join(res["unknown"]))
        if res.get("missing"):
            info.append("unfilled: " + ", ".join(res["missing"]))
        self.preview_info.setText("Preview with current sale data — "
                                  + ("OK" if not info else " | ".join(info)))

    # -- actions --
    def _do_save(self):
        rep = self._validation_report()
        problems = []
        if rep["unknown"]:
            problems.append("Unknown variables (will appear literally in contracts):\n- "
                            + "\n- ".join(rep["unknown"]))
        if rep["unbalanced_if"]:
            problems.append(f"Unbalanced {{IF}}/{{ENDIF}} "
                            f"({rep['if_open']} vs {rep['if_close']}).")
        if problems and QMessageBox.question(
                self, "Save template with warnings?",
                "\n\n".join(problems) + "\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._on_save(self._filename, self.editor.toPlainText())
        self.accept()

    def _do_reset(self):
        if QMessageBox.question(
                self, "Reset template",
                f"Discard your changes to {self._filename} and restore the bundled version?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._on_reset(self._filename)
        self.accept()
