"""Main window: thin coordinator (menubar + 4 views).

Responsibilities ONLY:
  - compose Generator / History / Presets / Templates views + shell menus
  - hold last render state (_last_text/_last_data/_last_res) + live-preview timer
  - delegate render → services.generation, files → document_service,
    persist → sale_service, presets/history/templates → views + repositories

Backwards-compat proxies (used by tests / old call sites):
  preset_cb, lang_cb, inputs, price_amount, price_currency,
  accept_check, preview, status, splitter, btn_gen/pdf/save, tabs
"""
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from ..database.repositories import get_preset, list_presets
from ..database.seed import ensure_seed
from ..version import __version__ as APP_VERSION
from ..services import document_service as docs
from ..services.export import export_pdf
from ..services.generation import compute_term_end, generate, sha256_text
from ..services.sale_service import save_current_sale
from ..services.settings import load as load_settings
from ..utils.paths import db_path, styles_path
from .settings_dialog import SettingsDialog
from .constants import PREVIEW_DEBOUNCE_MS, TERM_MIN_YEARS, TERM_MAX_YEARS
from ..engine.policy import IPI_PATTERN
from .shell import build_shell
from .views.generator_view import GeneratorView
from .views.history_view import HistoryView
from .views.presets_view import PresetsView
from .views.templates_view import TemplatesView

LEGAL_TEXT = (
    "TRAKKLICENSE is a self-help document tool, not a law firm and not legal advice. "
    "No attorney-client relationship is created. Use at your own risk and judgment — "
    "the final responsibility lies with you. Verify every license with a licensed "
    "attorney in your jurisdiction. See README.md § Legal Disclaimer.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TRAKKLICENSE v{APP_VERSION} — offline beat license generator")
        self.resize(1200, 750)
        ensure_seed(db_path())
        self._settings = load_settings()
        self._last_text = ""
        self._last_data = {}
        self._last_res: dict = {}
        self._split_init = False

        self.tabs = QStackedWidget()
        self.setCentralWidget(self.tabs)
        self.generator = GeneratorView()
        self.history = HistoryView(on_notice=self.generator.show_status)
        self.presets = PresetsView(on_status=self.generator.show_status)
        self.templates = TemplatesView(on_status=self.generator.show_status,
                                       preview_fn=self.preview_template_text)
        for v in (self.generator, self.history, self.presets, self.templates):
            self.tabs.addWidget(v)

        build_shell(self, self.tabs, {
            "generate": self.on_generate,
            "export_pdf": self.on_export_pdf,
            "save": self.on_save,
            "settings": self.on_settings,
            "close": self.close,
            "legal": self._show_legal,
            "about": self._show_about,
            "show_view": self.tabs.setCurrentIndex,
        })

        # wire generator buttons + live preview (400ms debounce)
        self.generator.btn_gen.clicked.connect(self.on_generate)
        self.generator.btn_pdf.clicked.connect(self.on_export_pdf)
        self.generator.btn_save.clicked.connect(self.on_save)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self.on_generate)
        self.generator.form_changed.connect(self._schedule_preview)

        self.presets.changed.connect(self.reload_presets)
        self.templates.changed.connect(self._on_templates_changed)
        self.reload_presets()
        # tier switch fills tier-linked fields (BeatStars semantics), then end recomputes
        self.generator.preset_cb.currentIndexChanged.connect(self._on_preset_changed)
        self.generator.inputs["CONTRACT_DATE"].textChanged.connect(self._refresh_term_end)
        self.generator.inputs["TERM_YEARS"].textChanged.connect(self._refresh_term_end)
        self._on_preset_changed()
        if self._settings.get("default_language") in ("English", "Español"):
            self.generator.lang_cb.setCurrentText(self._settings["default_language"])
        if self._settings.get("default_currency"):
            self.generator.price_currency.setCurrentText(self._settings["default_currency"])
        self.generator.apply_profile(self._settings)

        # FIX: frozen .exe keeps styles.qss in _MEIPASS — resolve via styles_path().
        try:
            qss = styles_path()
        except Exception:
            qss = Path(__file__).with_name("styles.qss")
        if qss.exists():
            self.setStyleSheet(qss.read_text(encoding="utf-8"))
        self.on_generate()

    # -- compat proxies (tests + old call sites read w.<name>) --
    @property
    def preset_cb(self):
        return self.generator.preset_cb

    @property
    def lang_cb(self):
        return self.generator.lang_cb

    @property
    def inputs(self):
        return self.generator.inputs

    @property
    def price_amount(self):
        return self.generator.price_amount

    @property
    def price_currency(self):
        return self.generator.price_currency

    @property
    def accept_check(self):
        return self.generator.accept_check

    @property
    def preview(self):
        return self.generator.preview

    @property
    def status(self):
        return self.generator.status

    @property
    def splitter(self):
        return self.generator.splitter

    @property
    def btn_gen(self):
        return self.generator.btn_gen

    @property
    def btn_pdf(self):
        return self.generator.btn_pdf

    @property
    def btn_save(self):
        return self.generator.btn_save

    @property
    def hist_list(self):
        return self.history.list

    @property
    def hist_view(self):
        return self.history.view

    @property
    def preset_list(self):
        return self.presets.list

    def showEvent(self, event):
        super().showEvent(event)
        if not self._split_init and self.splitter.width() > 0:
            self.generator.apply_initial_split()
            self._split_init = True

    # -- presets combo --
    def reload_presets(self):
        self.generator.preset_cb.clear()
        for p in list_presets(db_path()):
            self.generator.preset_cb.addItem(f"{p['name']} [{p['kind']}]", p["id"])

    def current_preset(self):
        pid = self.generator.preset_cb.currentData()
        return get_preset(db_path(), int(pid)) if pid is not None else None

    def collect(self) -> tuple[dict, str]:
        return self.generator.collect_form(self.current_preset())

    def _on_templates_changed(self):
        """Library or content changed → refresh preset options + live preview."""
        self.presets.reload_template_options()
        self.on_generate()

    def preview_template_text(self, template_text: str) -> dict:
        """Render draft template text with current sale data (editor Preview tab)."""
        from ..engine.renderer import render
        from ..services.generation import build_render_data
        from ..services.template_service import validate_template
        form, _kind = self.collect()
        data = build_render_data(form, self._resolve_preset())
        text, missing = render(template_text, data)
        unknown = validate_template(template_text)["unknown"]
        return {"rendered": text, "missing": sorted(missing), "unknown": unknown}

    #: form fields owned by the tier (refilled on tier switch; user-editable after)
    TIER_FIELDS = ("FILE_TYPE", "TERM_YEARS", "ROYALTY_AMOUNT", "PUBLISHING_SHARES",
                   "DISTRIBUTE_COPIES", "AUDIO_STREAMS")

    def _on_preset_changed(self, *args):
        self._apply_preset_defaults()
        self._refresh_term_end()

    def _apply_preset_defaults(self):
        """Tier switch fills its commercial values into the sale form."""
        preset = self.current_preset()
        if not preset:
            return
        mapping = {"FILE_TYPE": "file_type", "TERM_YEARS": "term_years",
                   "ROYALTY_AMOUNT": "royalty", "PUBLISHING_SHARES": "publishing_shares",
                   "DISTRIBUTE_COPIES": "distribute_copies", "AUDIO_STREAMS": "audio_streams"}
        for field, key in mapping.items():
            self.generator.inputs[field].setText(str(preset.get(key, "")))

    #: hard policy for the term field (QIntValidator alone doesn't enforce it —
    #: Qt lets typing/paste/setText through; this choke point normalizes).
    TERM_MIN, TERM_MAX = TERM_MIN_YEARS, TERM_MAX_YEARS

    def _refresh_term_end(self, *args):
        """TERM_END = effective date + sale TERM_YEARS.

        Single choke point: blank/garbage fall back to the tier default,
        out-of-range values clamp to TERM_MIN..TERM_MAX, and the field is
        rewritten so display, render and history always agree (no silent 999s).
        """
        field = self.generator.inputs["TERM_YEARS"]
        raw = field.text().strip()
        fallback = (self.current_preset() or {}).get("term_years", "")
        try:
            years = max(self.TERM_MIN, min(self.TERM_MAX, int(raw))) if raw else fallback
        except (ValueError, TypeError):
            years = fallback
        if str(years) != raw:
            field.blockSignals(True)
            try:
                field.setText(str(years))
            finally:
                field.blockSignals(False)
        end = compute_term_end(self.generator.inputs["CONTRACT_DATE"].text(), years)
        w = self.generator.inputs["TERM_END"]
        if w.text() != end:
            w.setText(end)  # triggers form_changed → live preview refresh

    # -- render / export / save --
    def _schedule_preview(self, *args):
        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def _resolve_preset(self):
        preset = self.current_preset()
        if preset and self.generator.lang_cb.currentText() == "Español":
            from ..services.template_service import template_exists
            base = preset.get("template_file", "")
            # Suffix swap only: replace() hit every ".md" in custom names.
            if base.lower().endswith(".md"):
                es_variant = base[:-3] + "_ES.md"
            else:
                es_variant = ""
            if es_variant and template_exists(es_variant):
                preset = dict(preset, template_file=es_variant)
            elif base:
                # FIX: ES fallback was silent — surface it so the user knows
                # the contract rendered in English.
                self.generator.show_status(
                    f"Nota: sin variante ES para {base}, se usa el texto en inglés.")
        return preset

    def on_generate(self):
        self._preview_timer.stop()
        form, kind = self.collect()
        res = generate(form, self._resolve_preset(), kind)
        self._last_text = res["text"]
        self._last_data = res["data"]
        self._last_res = res
        self.generator.show_preview(res["text"])
        msg = []
        if res["errors"]:
            msg.append("Missing: " + ", ".join(res["errors"]))
        if res["missing"]:
            msg.append("Unfilled vars: " + ", ".join(res["missing"]))
        # IPI format hint (CISAC: 9-11 digits). Warn only — a sale must
        # never be blocked by an identifier the buyer may not know yet.
        import re as _re
        for _k in ("PRODUCER_IPI", "CUSTOMER_IPI"):
            _v = str(res["data"].get(_k, "")).strip()
            if _v and not _re.fullmatch(IPI_PATTERN, _v):
                msg.append(f"{_k} format? (IPI is 9-11 digits)")
        # Price sanity: non-numeric or non-positive amounts pass validation
        # (field only required non-empty) but render without words. Warn only.
        _amt = str(res["data"].get("PRICE_AMOUNT", "")).strip().replace(",", "")
        try:
            _ok_price = float(_amt) > 0
        except (TypeError, ValueError):
            _ok_price = False
        if not _ok_price:
            msg.append("Price amount should be a number greater than zero")
        self.generator.show_status("OK" if not msg else " | ".join(msg))

    def _require_acceptance(self) -> bool:
        if not self._settings.get("require_acceptance", True):
            return True
        if self.generator.accept_check.isChecked():
            return True
        QMessageBox.warning(self, "Acceptance required",
                            "Check the acceptance box first: buyer has read and agrees "
                            "+ you have rights to license.")
        return False

    def _blockers_message(self, res: dict) -> str | None:
        """Literal-placeholder guard (PDF QC: no {VAR} left).

        Required-field `errors` only warn via status (preview still renders per
        QA) — but `missing` would print literally in the contract, so exports
        and saves are blocked with an explicit dialog.
        """
        missing = list((res or {}).get("missing") or [])
        if not missing:
            return None
        return ("Unfilled template variables would print literally in the contract:\n- "
                + "\n- ".join(missing)
                + "\n\nFill the sale form (or fix the template) before exporting.")

    def _flush_preview(self):
        """Regenerate now if a debounced preview is pending — exports must never use stale text."""
        # FIX (stale TERM_END): recompute the choke-point field first so display,
        # render and history always agree even on fast type → Export sequences.
        try:
            self._refresh_term_end()
        except Exception:
            pass
        if self._preview_timer.isActive():
            self.on_generate()
        elif not self._last_text:
            self.on_generate()

    def _auto_save(self) -> tuple[int, str]:
        """Folio + re-render + persist to history. Returns (sale_id, folio).

        Used by Save AND by exports: every exported document must carry a real
        folio (never DRAFT) and match its history record + evidence hash.
        """
        form, _kind = self.collect()
        preset = self._resolve_preset()
        out = save_current_sale(form, preset, self.generator.preset_cb.currentData())
        res = out["res"]
        self._last_text, self._last_data, self._last_res = res["text"], res["data"], res
        self.generator.show_preview(res["text"])
        self.history.reload()
        return out["sale_id"], out["folio"]

    def on_export_pdf(self):
        # FIX: normalize TERM_END before anything else (fast edit → Export race).
        try:
            self._refresh_term_end()
        except Exception:
            pass
        self._flush_preview()
        if not self._last_text:
            self.on_generate()
        if not self._require_acceptance():
            return
        blocker = self._blockers_message(self._last_res)
        if blocker:
            QMessageBox.warning(self, "Unfilled variables", blocker)
            self.generator.show_status(blocker.replace("\n", " "))
            return
        try:
            sid, saved_folio = self._auto_save()
            res = self._last_res or {}
            res.setdefault("text_hash", sha256_text(self._last_text))
            hash8, prefix, folio = docs.file_options(self._settings, self._last_data, res)
            footer = docs.evidence_footer(self._settings, res)
            p = export_pdf(self._last_text, docs.resolve_out_dir(self._settings),
                           self.generator.inputs["PRODUCT_TITLE"].text(),
                           self.generator.inputs["CUSTOMER_ALIAS"].text() or "customer",
                           self.generator.inputs["CONTRACT_DATE"].text(),
                           hash8, footer, prefix,
                           self._settings.get("pdf_pagesize", "LETTER"), folio,
                           docs.cover_data(self._settings, self._last_data, res),
                           brand=docs.brand_name(
                               self._settings,
                               self._last_data.get("PRODUCER_ALIAS", "")))
            tag = f"Auto-saved sale #{sid}" + (f" ({saved_folio})" if saved_folio else "")
            self.generator.show_status(f"{tag} → PDF saved: {p}")
            if self._settings.get("open_after_export", True):
                docs.open_file(p)
        except Exception as e:
            QMessageBox.warning(self, "PDF error", str(e))

    def on_save(self):
        try:
            self._refresh_term_end()
        except Exception:
            pass
        self._flush_preview()
        if not self._last_text:
            self.on_generate()
        if not self._require_acceptance():
            return
        blocker = self._blockers_message(self._last_res)
        if blocker:
            QMessageBox.warning(self, "Unfilled variables", blocker)
            self.generator.show_status(blocker.replace("\n", " "))
            return
        sid, folio = self._auto_save()
        self.generator.show_status(f"Saved sale #{sid}" + (f" — {folio}" if folio else ""))

    def on_settings(self):
        updated = SettingsDialog.edit(self)
        if updated:
            self._settings = updated
            if updated.get("default_language") in ("English", "Español"):
                self.generator.lang_cb.setCurrentText(updated["default_language"])
            if updated.get("default_currency"):
                self.generator.price_currency.setCurrentText(updated["default_currency"])
            self.generator.apply_profile(updated)
            self.generator.show_status("Settings saved")

    # -- history / presets delegation (kept for compat) --
    def reload_history(self):
        self.history.reload()

    def on_hist_open(self, item):
        self.history.open_item(item)

    def reload_preset_list(self):
        self.presets.reload()
        self.reload_presets()

    def on_preset_open(self, item=None):
        self.presets.open_item(item)

    def on_preset_dup(self):
        self.presets.duplicate()

    def on_preset_save(self):
        self.presets.save_changes()

    def on_preset_del(self):
        self.presets.delete()

    # -- samples compat (old call sites drove rows directly) --
    def collect_samples(self) -> str:
        return self.generator.samples.collect()

    def _show_about(self):
        QMessageBox.information(
            self, "About TRAKKLICENSE",
            f"TRAKKLICENSE v{APP_VERSION}\n"
            "Offline beat-license generator for beatmakers.\n"
            "Templates + variables → preview → PDF/MD. No accounts, no cloud.")

    def _show_legal(self):
        QMessageBox.information(self, "Legal disclaimer", LEGAL_TEXT)
