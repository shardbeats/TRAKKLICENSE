# QA — TRAKKLICENSE

Procedures before touching templates, DB or releases.

## 1. Levels
- **Unit** (`tests/test_*.py`): renderer, money_words, validators, database, services, export, templates no-leak.
- **Gherkin** (`features/*.feature` + `tests/test_gherkin.py`): license_generation (4 scenarios) + presets (3 scenarios). Same `pytest`.
- **Manual GUI**: `py main.py` → Generate preview → Export PDF (auto-saves) → History → Presets duplicate/edit → Templates new/edit/reset.
- **PDF QC**: every export must open, contain beat title + price, no `{VAR}` left.

## 2. Pre-commit (required)
```bat
py -3 -m pytest tests -q
```
Fast loop:
```bat
py -3 -m pytest tests -q -m "not slow" --no-cov
py -3 -m pytest tests -q -p no:cacheprovider --cov=app --cov-report=term-missing --cov-fail-under=80
```

## 3. Pre-release / template change
1. `pytest tests/ -q` green.
2. `py tools\quality_metrics.py` → gates PASS + `data/quality_report.json`.
3. Manual: generate 1 non-exclusive + 1 exclusive with demo data, export both PDFs, open them.
4. Verify: no `{UPPER_VAR}` remains, price words match price, term dates coherent.
5. Rebuild exe: `py build_exe.py` → test exe in clean folder (portable data/ created).

## 4. Manual GUI checklist
- [ ] Empty customer fullname → validation lists CUSTOMER_FULLNAME, preview still renders.
- [ ] Price "99 USD" without words → preview contains "ninety-nine USD".
- [ ] Exclusive preset → preview contains §25 ACCEPTANCE + 10-year.
- [ ] Export PDF exists in out/ with safe filename (folio, no DRAFT).
- [ ] Save → History shows `#id date — beat → artist (price)`, reopen shows full text.
- [ ] Presets: duplicate WAV Lease → edit price → appears in Generator combo.
- [ ] Presets: Duplicate + template → new tier linked to `_copy.md`, original untouched.
- [ ] Tiers: switching tier fills file/royalty/publishing/years/caps; editing years recomputes term end; backdating effective date shifts start+end; Exclusive shows unlimited caps.
- [ ] Templates: edit seed → override listed, Generator uses it, Reset restores bundled; unknown {VAR} warns on save.
- [ ] Delete temp preset works, seed 5 never duplicate on reseed.
- [ ] IPI: set producer IPI in Settings → Generator box auto-checked with it; uncheck → contract has no IPI lines; malformed IPI warns in status without blocking.
- [ ] IPI: customer address is always manual (profile never fills buyer domicile).
- [ ] Brand: explicit brand_name → form alias → profile alias → TRAKKLICENSE; cover eyebrow + footers match the licensor named in the text.
- [ ] Price "abc"/"-5" warns in status (`greater than zero`), preview still renders.
- [ ] Legal disclaimer available in Help menu.

## 5. PDF QC (per export)
- [ ] Opens in Edge/Acrobat, LETTER, readable.
- [ ] Contains beat title, parties, price, term, governing law.
- [ ] No `{VAR}` placeholders remain.
- [ ] Filename `TRAKKLICENSE_{beat}_{cust}_{date}.pdf`.

## 6. Rules
- Never commit `data/*.db`, `out/*`, `.venv/`, `__pycache__/`, real customer data.
- Template fix → test in `test_templates_qa.py` or `license_generation.feature`.
- Preset rule change → case in `presets.feature`.
- Personal data (names/IPI/addresses/beats reales) → test must fail (FORBIDDEN lists).
