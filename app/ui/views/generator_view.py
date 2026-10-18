"""Generator view: sale form (left) + live preview (right). Emits no DB/file I/O."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSplitter, QVBoxLayout, QWidget, QTextBrowser,
)

from ..constants import (
    CURRENCIES,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_AMOUNT,
    FIELDS,
    TERM_MAX_YEARS,
    TERM_MIN_YEARS,
)
from ..widgets.samples_widget import SamplesWidget
from ...services.generation import today_iso


class GeneratorView(QWidget):
    """Form + preview. Owner (MainWindow) wires DB, render and export callbacks."""

    form_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        self.splitter = splitter

        # --- left: form ---
        left = QWidget()
        left.setMaximumWidth(600)
        lf = QVBoxLayout(left)
        lf.setContentsMargins(0, 0, 0, 0)
        lf.setSpacing(4)

        lf.addWidget(QLabel("<b>Preset</b>"))
        self.preset_cb = QComboBox()
        lf.addWidget(self.preset_cb)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Template language:"))
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(["English", "Español"])
        lang_row.addWidget(self.lang_cb)
        lf.addLayout(lang_row)

        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(2)
        form.setHorizontalSpacing(8)
        self.inputs: dict[str, QLineEdit] = {}
        for key, label, default in FIELDS:
            w = QLineEdit(default)
            w.textChanged.connect(lambda _=None: self.form_changed.emit())
            self.inputs[key] = w
            form.addRow(label, w)
        # Effective date defaults to today; term start/end derive from it + years
        self.inputs["CONTRACT_DATE"].setText(today_iso())
        self.inputs["TERM_YEARS"].setValidator(QIntValidator(TERM_MIN_YEARS, TERM_MAX_YEARS, self))
        self.inputs["STATE_PROVINCE_COUNTRY"].setPlaceholderText("e.g. Texas, USA")
        self.inputs["TERM_END"].setReadOnly(True)
        self.inputs["TERM_END"].setPlaceholderText("auto: start + years")

        self.price_amount = QLineEdit(DEFAULT_PRICE_AMOUNT)
        self.price_amount.textChanged.connect(lambda _=None: self.form_changed.emit())
        self.price_currency = QComboBox()
        self.price_currency.setEditable(True)
        self.price_currency.addItems(CURRENCIES)
        self.price_currency.editTextChanged.connect(lambda _=None: self.form_changed.emit())
        self.price_currency.currentIndexChanged.connect(lambda _=None: self.form_changed.emit())
        price_row = QWidget()
        price_lay = QHBoxLayout(price_row)
        price_lay.setContentsMargins(0, 0, 0, 0)
        price_lay.addWidget(self.price_amount, 2)
        price_lay.addWidget(self.price_currency, 1)
        form.addRow("Price amount + currency", price_row)
        lf.addWidget(form_wrap)

        self.samples = SamplesWidget()
        self.samples.changed.connect(self.form_changed.emit)
        lf.addWidget(self.samples)

        # --- IPI identifiers (optional, checkbox-gated like SamplesWidget) ---
        self.ipi_group = QGroupBox("IPI identifiers (optional)")
        ipi_lay = QVBoxLayout(self.ipi_group)
        ipi_lay.setContentsMargins(6, 4, 6, 4)
        ipi_lay.setSpacing(2)
        self.ipi_check = QCheckBox("Include IPI identifiers in this license.")
        self.ipi_check.setToolTip(
            "IPI (Interested Party Information, 9-11 digits) links each party "
            "to its PRO (e.g. SACM, BMI, ASCAP) for royalty identification.")
        self.ipi_check.toggled.connect(self._on_ipi_toggled)
        ipi_lay.addWidget(self.ipi_check)
        self.ipi_rows = QWidget()
        ipi_form = QFormLayout(self.ipi_rows)
        ipi_form.setContentsMargins(0, 0, 0, 0)
        self.ipi_producer = QLineEdit()
        self.ipi_producer.setPlaceholderText("Producer IPI e.g. 12345678901")
        self.ipi_producer.textChanged.connect(lambda _=None: self.form_changed.emit())
        self.ipi_customer = QLineEdit()
        self.ipi_customer.setPlaceholderText("Customer IPI (often unknown — leave blank)")
        self.ipi_customer.textChanged.connect(lambda _=None: self.form_changed.emit())
        ipi_form.addRow("Producer IPI", self.ipi_producer)
        ipi_form.addRow("Customer IPI", self.ipi_customer)
        self.ipi_rows.setVisible(False)
        ipi_lay.addWidget(self.ipi_rows)
        lf.addWidget(self.ipi_group)

        self.accept_check = QCheckBox(
            "Buyer has read and agrees + I have rights to license (18+, samples cleared).")
        lf.addWidget(self.accept_check)

        actions = QHBoxLayout()
        self.btn_gen = QPushButton("Generate (F5)")
        self.btn_pdf = QPushButton("Export PDF")
        self.btn_save = QPushButton("Save")
        for b in (self.btn_gen, self.btn_pdf, self.btn_save):
            actions.addWidget(b)
        lf.addLayout(actions)
        self.status = QLabel("Ready.")
        self.status.setWordWrap(True)
        lf.addWidget(self.status)

        # --- right: preview ---
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("<b>Preview</b>"))
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        rl.addWidget(self.preview)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter)

        self.preset_cb.currentIndexChanged.connect(lambda _=None: self.form_changed.emit())
        self.lang_cb.currentIndexChanged.connect(lambda _=None: self.form_changed.emit())

    # -- public API --
    def collect_form(self, preset: dict | None) -> tuple[dict, str]:
        import re
        form = {k: w.text().strip() for k, w in self.inputs.items()}
        form["PRICE_AMOUNT"] = self.price_amount.text().strip()
        # FIX: free-typing "XXX"/typos used to flow into PRODUCT_PRICE and the
        # PDF. Coerce to known codes, default policy currency.
        cur = self.price_currency.currentText().strip().upper() or DEFAULT_CURRENCY
        if cur not in CURRENCIES:
            cur = cur if re.fullmatch(r"[A-Z]{3}", cur or "") else DEFAULT_CURRENCY
        form["PRICE_CURRENCY"] = cur
        form["SAMPLES"] = self.samples.collect()
        form["SAMPLES_CONFIRMED"] = "1" if self.samples.is_confirmed() else "0"
        if self.ipi_check.isChecked():
            form["PRODUCER_IPI"] = self.ipi_producer.text().strip()
            form["CUSTOMER_IPI"] = self.ipi_customer.text().strip()
        else:
            form["PRODUCER_IPI"] = ""
            form["CUSTOMER_IPI"] = ""
        kind = (preset or {}).get("kind", "non-exclusive")
        # NOTE: LICENSE_NAME default lives in generation.build_render_data
        # (legal term from kind, never the commercial tier name).
        return form, kind

    def _on_ipi_toggled(self, checked: bool):
        self.ipi_rows.setVisible(checked)
        self.form_changed.emit()

    def apply_profile(self, settings: dict, overwrite: bool = False):
        # NOTE: profile_location no longer autofills CUSTOMER_ADDRESS — the
        # producer's location must never print as the buyer's domicile.
        # Customer address is always typed per sale.
        pairs = (
            ("PRODUCER_ALIAS", "profile_alias"),
            ("PRODUCT_OWNER_FULLNAME", "profile_owner"),
            ("STATE_PROVINCE_COUNTRY", "profile_state_country"),
        )
        for field, key in pairs:
            val = (settings.get(key) or "").strip()
            w = self.inputs.get(field)
            if w is not None and val and (overwrite or not w.text().strip()):
                w.setText(val)
        # Producer IPI lives in the profile (stable identity): prefill once,
        # and opt the sale in automatically so it flows into every license.
        ipi = (settings.get("profile_producer_ipi") or "").strip()
        if ipi and (overwrite or not self.ipi_producer.text().strip()):
            self.ipi_producer.setText(ipi)
        if self.ipi_producer.text().strip() and not self.ipi_check.isChecked():
            self.ipi_check.setChecked(True)

    def show_preview(self, text: str):
        # FIX: preview used to truncate at 20000 chars while export used the
        # full text — the user validated a cropped contract. Show everything.
        self.preview.setMarkdown(text or "")

    def show_status(self, msg: str):
        self.status.setText(msg)

    def apply_initial_split(self, form_frac: float = 0.32):
        if self.splitter.width() > 0:
            total = self.splitter.width()
            self.splitter.setSizes([int(total * form_frac), int(total * (1 - form_frac))])
