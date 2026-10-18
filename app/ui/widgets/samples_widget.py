"""Loops & Samples widget (BeatStars-style). No DB, no file I/O — pure form widget."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from ...services.generation import compose_samples


class SamplesWidget(QGroupBox):
    """Checkbox + dynamic (name, source) rows. Emits `changed` on any edit."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__("Loops and Samples", parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)

        self.check = QCheckBox("This track contains 3rd party loops and/or samples.")
        self.check.toggled.connect(self._on_toggled)
        lay.addWidget(self.check)

        self.note = QLabel(
            "Note: By checking this box, you confirm you have full legal rights "
            "to use these samples/loops.")
        self.note.setWordWrap(True)
        self.note.setVisible(False)
        lay.addWidget(self.note)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMaximumHeight(88)
        self.scroll.setVisible(False)
        inner = QWidget()
        self.rows_lay = QVBoxLayout(inner)
        self.rows_lay.setContentsMargins(0, 0, 4, 0)
        self.rows_lay.setSpacing(2)
        self.scroll.setWidget(inner)
        lay.addWidget(self.scroll)

        self.btn_add = QPushButton("+ Add new")
        self.btn_add.clicked.connect(lambda: self.add_row())
        self.btn_add.setVisible(False)
        lay.addWidget(self.btn_add)

        self._rows: list[tuple[QLineEdit, QLineEdit, QWidget]] = []

    # -- public API --
    def is_confirmed(self) -> bool:
        return self.check.isChecked()

    def set_confirmed(self, value: bool):
        self.check.setChecked(value)

    def collect(self) -> str:
        items = [(n.text(), s.text()) for n, s, _ in self._rows]
        return compose_samples(items, self.is_confirmed())

    def add_row(self, name: str = "", source: str = ""):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        n = QLineEdit(name)
        n.setPlaceholderText("What's the name?")
        n.textChanged.connect(lambda _=None: self.changed.emit())
        s = QLineEdit(source)
        s.setPlaceholderText("Source")
        s.textChanged.connect(lambda _=None: self.changed.emit())
        rm = QPushButton("🗑")
        rm.setFixedWidth(36)
        rm.clicked.connect(lambda: self.remove_row(row))
        lay.addWidget(n, 2)
        lay.addWidget(s, 2)
        lay.addWidget(rm, 0)
        self.rows_lay.addWidget(row)
        self._rows.append((n, s, row))
        self.changed.emit()

    def remove_row(self, row: QWidget):
        for n, s, w in list(self._rows):
            if w is row:
                self.rows_lay.removeWidget(w)
                w.deleteLater()
                self._rows.remove((n, s, w))
                self.changed.emit()
                break

    # -- internals --
    def _on_toggled(self, checked: bool):
        self.note.setVisible(checked)
        self.scroll.setVisible(checked)
        self.btn_add.setVisible(checked)
        if checked and not self._rows:
            self.add_row()
        self.changed.emit()
