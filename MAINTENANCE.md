# MAINTENANCE — TRAKKLICENSE

Operations handover for keeping this project healthy. Read before touching validation, render, templates, DB, or releases.

## Environment
- System Python 3.14 (`.venv` in project root). Deps: `PySide6>=6.6,<7`, `reportlab>=4.0` (+ pytest, pytest-cov, pytest-bdd, pytest-timeout for tests).
- `start.bat` creates `.venv`, installs `requirements.txt`, launches with the venv Python and tees output to `data\launch.log`. `run.bat` relaunches. Both use `python.exe`, never `pythonw.exe` (pythonw hides tracebacks — failures were silent).
- User data lives **outside the repo**: source runs use `%APPDATA%\TRAKKLICENSE\` (`trakklicense.db`, `out\`, `templates\`, `settings.json`); the frozen `.exe` uses portable `data\` next to the exe. `TRAKKLICENSE_DATA_DIR` overrides both (tests use it with `tmp_path`). Never commit `data/*.db`, `out/*`, `.venv/`, real customer data. A deleted DB reseeds empty on boot (`ensure_seed`).
- GUI tests need a display: offscreen via `QT_QPA_PLATFORM=offscreen` (set per-test with monkeypatch). `TRAKKLICENSE_SKIP_GUI=1` skips them (coverage then lies — see gotchas).
- PowerShell 5.1: native exes need the call operator — `& ".venv\Scripts\python.exe" -m pytest …` (bare `".venv\…" -m …` parses `-m` as a PowerShell token and fails).

## Routines
```bat
.venv\Scripts\python -m pytest tests -q                :: full suite (97 tests) + coverage gate ≥80%, must pass before any change
.venv\Scripts\python -m pytest tests -q -p no:cacheprovider --no-cov -m "not slow"  :: fast loop
.venv\Scripts\python tools\quality_metrics.py          :: gates PASS → data\quality_report.json (pass 100%, cov ≥80%, PDF smoke, gherkin)
.venv\Scripts\python main.py                           :: run (same as run.bat)
.venv\Scripts\python build_exe.py                      :: tests + windowed dist\TRAKKLICENSE.exe (~60 MB, bundles styles.qss + seeds)
.venv\Scripts\python build_exe.py --console             :: console build for diagnostics
```

## Layer rules (important)
- Strict layers: `ui → services → engine/database → SQLite`. `app/engine/` is pure Python (no Qt, no DB, no I/O): `renderer` (`{VAR}`/`{{var}}` case-insensitive + single-level `{IF}`/`{ENDIF}`, no ELSE/nesting), `variables.VARIABLES` (the contract every template is scanned against), `validators` (required-field lists), `money_words` (0..999999, EN+ES).
- `app/services/generation.generate()` is the only render entry: UI, gherkin and tests go through it. It returns `{text, missing, errors, data, template_file, template_version, text_hash}`.
- `build_render_data()` merges form + preset + autos. Rules: empty-string form fields fall back to the tier (never `setdefault` — the UI always sends every key, so `setdefault` keeps `""` and prints blank lines); every `VARIABLES` key defaults to `""` (known keys never print literally); explicit values (TERM_END, COUNTRY, LICENSE_NAME) are respected; `*_WORD` autos pass `unlimited` through.
- `sale_service.save_current_sale()` is the only persist entry: assigns folio via `settings.next_folio()`, stamps `FOLIO`, **re-renders** (hash covers final text), maps to `repositories.save_sale()`. Saved text never says DRAFT (folio `""` when disabled, never the literal).
- `settings.next_folio()/save()` are mkdir-locked + atomic (`tmp → os.replace`). Folios are never reused (deletes don't recycle); gaps on failed saves are by design, duplicates are the bug being prevented.
- `MainWindow` is a thin coordinator (holds `_last_text/_last_data/_last_res` + 400ms debounce timer). `TERM_END` is recomputed in `_refresh_term_end()` (clamp 1–100 per `constants.py`, the single source of truth — `QIntValidator` is cosmetic) and refreshed before every preview/export (fast type → Export race wrote stale dates once).
- `utils/paths.py` is frozen-aware: `sys.frozen` → `data/` next to `sys.executable`; `templates_dir()/styles_path()` prefer `sys._MEIPASS`. `build_exe.py` uses `os.pathsep` for `--add-data` (`;` is Windows-only).
- `template_service`: bundled seeds (read-only, ships in exe) + user overrides (`<base>/templates/`, copy-on-write, Reset deletes the override). `template_version` is content-hash based, so custom edits are tracked by history warnings with no extra code.
- `features/*.feature` state the contract: behavior change = update feature + steps in the same commit.

## Test inventory (110 via quality_metrics: 103 direct + 7 gherkin)
- `test_renderer.py` (5): `{}`/`{{}}`/alias/`IF`/missing-set semantics.
- `test_engine_edge.py` (4) + `test_words_fallback.py` (2): renderer edges, ES words fallback.
- `test_money_words.py` (3): cents (`49.99` → `forty-nine and 99/100 USD`), currency passthrough.
- `test_term_dates.py` (11): `compute_term_end` (leap→Feb28, overflow→`""`), blank-end autofill vs explicit-end respected, GUI start=today/end=auto, tier switch fills form, clamp 1–100. Pinned strings: `"3 years from"` in non-exclusive text.
- `test_bugfixes.py` (15): cover escaping, cents flow, samples-checked-empty→`SAMPLES` error, FK delete returns False, folio-off saves `""` not DRAFT, history delete keeps folio sequence, export auto-saves real folio, stale-flush, tier-name hiding, COUNTRY derivation, governing combo removed, price warning without blocking, `profile_location` never fills buyer address.
- `test_exclusive_template.py` (4): renders clean with fixed SAMPLE, no personal-data leak (FORBIDDEN list), exclusive validators.
- `test_templates_qa.py` (1): every seed template var ∈ VARIABLES + no-leak scan over all 4 seeds.
- `test_template_service.py` (6) + `test_template_editor.py` (3): user-first resolution, shadow/override/reset, guide/preview/warn-save. NOTE: bundled seeds must not contain the lowercase substring `custom` (`"customary"` broke `test_user_shadows_bundled` once — use `standard`).
- `test_database.py` (1) + `test_migration.py` (1): seed-5 + legacy price-column migration.
- `test_evidence.py` (5) + `test_folio_profile.py` (3): sha/version/hash evidence, folio `LIC-YYYY-NNNN` rollover + profile autofill.
- `test_services.py` (2) + `test_services_refactor.py` (6) + `test_coverage_boost.py` (6): generate non-exclusive, file_options (DRAFT kept for preview filenames — pinned), folio/save flow, cover toggle, out-dir resolve.
- `test_settings.py` (6) + `test_shell.py` (1): settings roundtrip/sanitize, dialog currency coercion, menubar-only (no toolbars).
- `test_pdf_design.py` (2): cover + inline-md escaping.
- `test_gherkin.py` (7 scenarios via `test_gherkin.py` steps): WAV lease clean + valid, empty CUSTOMER_FULLNAME → validation, `99 USD` → `ninety-nine USD`, exclusive has `25. ACCEPTANCE` + `10-year` + no leak; reseed stays 5, duplicate Plus, temp create/delete.
- `test_ipi.py` (6): `{IF}` IPI blocks render only when filled (all 4 seeds), empty defaults, sale persistence, cover rows, profile autofill + checkbox gate, malformed-IPI warns without blocking.
- `test_brand.py` (7): `brand_name` resolution (explicit → sale alias → profile → default), settings roundtrip, cover eyebrow uses brand (no TRAKKLICENSE leak), `export_pdf` default preserved, GUI export passes alias/explicit brand through.
- `test_version.py` (3): `app/version.py` X.Y.Z + pyproject/builders parse it, crash handler writes `error.log` offscreen, title carries version + Help > About.

## PDF QC (per export, see QA.md §5)
Opens in Edge/Acrobat, LETTER (or A4 per settings), contains beat title + parties + price + term + governing law, no `{VAR}` remains, filename `TRAKKLICENSE_{beat}_{cust}_{date}[_{folio}][_{hash8}].pdf`. Same-beat re-exports append `_2`, `_3`… (never overwrite).

## Known gotchas
- `setdefault` vs `""`: the form always sends every key, so `data.setdefault("FILE_TYPE", …)` keeps `""`. Empty-check-then-fill is the rule for all tier-backed fields.
- `TERM_END` goes stale on fast type → Export: `_flush_preview`/`on_export_pdf`/`on_save` all call `_refresh_term_end()` first; `build_render_data` only fills blank ends (explicit respected, pinned by tests).
- `file_options` keeps `DRAFT` when `filename_folio` is on (preview filenames — pinned by test); exports never see DRAFT because `_auto_save` stamps the real folio first. Don't "simplify" this away.
- `_migrate_preset_caps` backfills `unlimited` only when the columns are newly added; running it every `init_db()` clobbered deliberate `5000/500000` exclusive edits on restart.
- `create_preset`: `preset.get(k, default)` keeps explicit `None` (NOT NULL violation) — empty/None fall back to tier defaults; duplicate names raise `ValueError` (UI shows a dialog), not raw `IntegrityError`.
- `get/delete/update` repositories all call `init_db()` (fresh/legacy DBs open clean).
- `validators.validate` is case-insensitive on kind (`"Exclusive"` == `"exclusive"`).
- Preview/history/editor show the full text (no `[:20000]` truncation — the user validated a cropped contract once). History/template list items carry ids/names in `UserRole`, never parsed from labels (titles with `#`, names with ` [` broke this).
- Orphan tier template (file deleted externally) shows `[missing]` + status warning and blocks save until reassigned.
- ES fallback is announced in status (was silent); `LICENSE_NAME` ES translation only applies to auto-derived values.
- `collect_form` coerces currency to 3-letter codes or USD (free-typed `XXX` reached contracts once).
- `QSS` styles `:disabled`/`:focus`/`QMessageBox` explicitly (global `QWidget` background flattened dialogs/focus once).
- `compute_term_end` had a dead duplicate `except ValueError` (removed).
- `money_to_words` raises on negatives/out-of-range: price path swallows to missing `PRICE_WORD` (validation flags the price); copies/streams catch `(ValueError, TypeError)` and pass raw values through.

## Don't touch without reason
- `app/version.py` (`__version__` X.Y.Z — pyproject/build_exe read it; bump per release).
- `app/engine/policy.py` (single source for template names, caps, currencies, folio format, hash length — every layer imports it; never redefine these literals elsewhere).
- `app/database/connection.py::SCHEMA` (column changes → add a `_migrate_*` like `_migrate_sales_ipi`; old user DBs only get columns via migrations).
- `app/engine/variables.py::VARIABLES` (adding a key requires: template `{IF}`-guard if optional, `FIELDS`/profile wiring if user-fillable, `sale_service` mapping + migration if persisted, ES mirror, cases in `test_ipi.py`-style coverage).
- `app/seed_templates/*.md` wording (gherkin pins `25. ACCEPTANCE`, `10-year`, `3 years from`; no-leak scan pins no personal data and no lowercase `custom`; every `{VAR}` must be in VARIABLES).
- `features/*.feature` + `tests/test_gherkin.py` steps (the business contract).
- Folio semantics (locked counter, yearly reset, never reused) and evidence fields (`text_hash`/`template_version`/`accepted_at`).
- `TIER_FIELDS` + `_apply_preset_defaults` + `TERM_MIN/MAX_YEARS` choke points (term policy lives there).

## Typical change checklist
1. Template wording → keep all `{VARS}` in VARIABLES → ES mirror → `pytest` → `quality_metrics.py` → render all 4 seeds + export both PDFs and open them (QA.md §3).
2. New variable → VARIABLES → `{IF}`-guard if optional → form/profile wiring → `build_render_data` default → sale mapping + `_migrate_*` → cover if evidence → tests → QA §4.
3. Preset/tier rule → case in `features/presets.feature` (+ `test_term_dates.py` if term-related).
4. Validation rule → `engine/validators.py` (+ `generate()` samples guard pattern) → status message in `on_generate`, never a modal on `errors` (preview must still render; only literal-placeholder `missing` blocks export/save).
5. UI change → offscreen GUI test (`QT_QPA_PLATFORM=offscreen`, `TRAKKLICENSE_DATA_DIR=tmp_path` pattern) → full `pytest` (GUI tests affect coverage).
6. Release → bump `app/version.py` → `pytest` green → `quality_metrics.py` PASS → manual 1 non-exclusive + 1 exclusive with demo data, open both PDFs → `py build_exe.py` → test exe in a clean folder (portable `data/` created next to it). Distribution is the portable exe + README (no installer shipped: offline app, no third-party binaries to bundle).
- Frozen crashes: windowed exes have `stdout=None` — `main.py` redirects stdio to `<base>/trakklicense.log` and hooks uncaught exceptions to `<base>/error.log` + dialog (`app/utils/crash.py`, offscreen-safe). Never write user data under `sys._MEIPASS`.
- `start.bat` rejects the Microsoft Store python stub and sanity-checks a fresh venv; keep those checks when editing bats.
