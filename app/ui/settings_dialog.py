"""Settings dialog: output of documents (filenames, footer, PDF, defaults)."""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QHBoxLayout, QFileDialog, QLabel, QWidget,
)

from ..engine.policy import DEFAULT_BRAND, DEFAULT_CURRENCY, FOLIO_PREFIX
from ..services.settings import load, save
from .constants import CURRENCIES


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TRAKKLICENSE — Settings (document output)")
        self.setMinimumWidth(480)
        s = load()

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<b>Document output</b> (applies to PDF exports)"))
        form = QFormLayout()

        self.out_dir = QLineEdit(s["out_dir"])
        self.out_dir.setPlaceholderText("Empty = default out/ folder")
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.out_dir)
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.clicked.connect(self.on_browse)
        browse_row.addWidget(self.btn_browse)
        brow = QWidget()
        brow.setLayout(browse_row)
        form.addRow("Output folder", brow)

        self.prefix = QLineEdit(s["filename_prefix"])
        form.addRow("Filename prefix", self.prefix)
        self.brand = QLineEdit(s.get("brand_name", ""))
        self.brand.setPlaceholderText("Empty = producer alias, else TRAKKLICENSE")
        form.addRow("Document brand", self.brand)
        self.ck_hash = QCheckBox("Append short hash to filename")
        self.ck_hash.setChecked(s["filename_hash"])
        form.addRow("", self.ck_hash)
        self.ck_folio_name = QCheckBox("Include folio in filename")
        self.ck_folio_name.setChecked(s["filename_folio"])
        form.addRow("", self.ck_folio_name)
        self.ck_folio = QCheckBox(f"Assign folio {FOLIO_PREFIX}YYYY-NNNN on save")
        self.ck_folio.setChecked(s["folio_enabled"])
        form.addRow("", self.ck_folio)
        self.ck_cover = QCheckBox("PDF cover page (title / parties / price / folio)")
        self.ck_cover.setChecked(s["pdf_cover"])
        form.addRow("", self.ck_cover)
        self.ck_open = QCheckBox("Open document after export")
        self.ck_open.setChecked(s["open_after_export"])
        form.addRow("", self.ck_open)
        self.ck_footer = QCheckBox("Append Evidence footer to exports")
        self.ck_footer.setChecked(s["footer_evidence"])
        form.addRow("", self.ck_footer)
        self.ck_accepted = QCheckBox("Include Accepted timestamp in footer")
        self.ck_accepted.setChecked(s["footer_accepted"])
        form.addRow("", self.ck_accepted)

        self.pagesize = QComboBox()
        self.pagesize.addItems(["LETTER", "A4"])
        self.pagesize.setCurrentText(s["pdf_pagesize"])
        form.addRow("PDF page size", self.pagesize)

        lay.addWidget(QLabel("<b>Sale form defaults</b>"))
        form2 = QFormLayout()
        self.lang = QComboBox()
        self.lang.addItems(["English", "Español"])
        self.lang.setCurrentText(s["default_language"])
        form2.addRow("Template language", self.lang)
        self.currency = QComboBox()
        self.currency.setEditable(True)
        self.currency.addItems(CURRENCIES)
        self.currency.setCurrentText(s["default_currency"])
        form2.addRow("Currency", self.currency)
        self.ck_require = QCheckBox("Require acceptance checkbox before export/save")
        self.ck_require.setChecked(s["require_acceptance"])
        form2.addRow("", self.ck_require)
        lay.addLayout(form)
        lay.addLayout(form2)

        lay.addWidget(QLabel("<b>Producer profile</b> (autofills the sale form)"))
        form3 = QFormLayout()
        self.prof_alias = QLineEdit(s["profile_alias"])
        form3.addRow("Producer alias", self.prof_alias)
        self.prof_owner = QLineEdit(s["profile_owner"])
        form3.addRow("Owner fullname", self.prof_owner)
        self.prof_ipi = QLineEdit(s.get("profile_producer_ipi", ""))
        self.prof_ipi.setPlaceholderText("e.g. 12345678901 (optional, 9-11 digits)")
        form3.addRow("Producer IPI", self.prof_ipi)
        self.prof_state = QLineEdit(s["profile_state_country"])
        form3.addRow("State, Country", self.prof_state)
        lay.addLayout(form3)

        btns = QHBoxLayout()
        self.btn_ok = QPushButton("Save")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        lay.addLayout(btns)

    def _coerced_currency(self) -> str:
        """Same rule as the sale form: known codes pass, else 3-letter code or default."""
        import re
        cur = self.currency.currentText().strip().upper() or DEFAULT_CURRENCY
        if cur not in CURRENCIES:
            cur = cur if re.fullmatch(r"[A-Z]{3}", cur or "") else DEFAULT_CURRENCY
        return cur

    def on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d:
            self.out_dir.setText(d)

    def result_patch(self) -> dict:
        return {
            "out_dir": self.out_dir.text().strip(),
            "filename_prefix": self.prefix.text().strip() or DEFAULT_BRAND,
            "brand_name": self.brand.text().strip(),
            "filename_hash": self.ck_hash.isChecked(),
            "filename_folio": self.ck_folio_name.isChecked(),
            "folio_enabled": self.ck_folio.isChecked(),
            "pdf_cover": self.ck_cover.isChecked(),
            "open_after_export": self.ck_open.isChecked(),
            "footer_evidence": self.ck_footer.isChecked(),
            "footer_accepted": self.ck_accepted.isChecked(),
            "pdf_pagesize": self.pagesize.currentText(),
            "default_language": self.lang.currentText(),
            "default_currency": self._coerced_currency(),
            "require_acceptance": self.ck_require.isChecked(),
            "profile_alias": self.prof_alias.text().strip(),
            "profile_owner": self.prof_owner.text().strip(),
            "profile_producer_ipi": self.prof_ipi.text().strip(),
            "profile_state_country": self.prof_state.text().strip(),
        }

    @staticmethod
    def edit(parent=None) -> dict | None:
        dlg = SettingsDialog(parent)
        if dlg.exec():
            return save(dlg.result_patch())
        return None
