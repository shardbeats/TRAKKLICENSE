# TRAKKLICENSE

Offline beat-license generator for beatmakers. Part of ShardBeats TRAKK SUITE.

Templates + editable variables → live preview → PDF/MD with evidence footer. No accounts, no cloud.

## Quick start (dev)
```bat
start.bat      :: creates .venv, installs requirements, launches (logs to data\launch.log)
run.bat        :: launch with existing .venv
```

Manual:
```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest tests -q
```

## How it works
```
Tier (Presets) + sale form (Generator) → build_render_data() [auto *_WORD, TERM_*, COUNTRY, FOLIO=DRAFT]
  → generate() renders the tier's template → live preview
  → Save / Export PDF: folio LIC-YYYY-NNNN assigned, text re-rendered with the real
    folio, persisted to history (SQLite) with SHA256 + template version, PDF/MD exported to out/
```

- **Preview never blocks**: missing required fields only warn in the status bar (`Missing: …`).
- **Export/Save block only on literal placeholders**: if a template variable would print
  as `{VAR}` in the contract, export is stopped with an explicit dialog (PDF QC: no `{VAR}` left).
- Every export auto-saves first, so the file always carries a real folio (never `DRAFT`)
  matching its history record. Folios are never reused, even after deleting a sale.
- `TERM_END` is a choke-point field: effective date + years, clamped to 1–100, recomputed
  before every preview/export so display, contract and history always agree.
- Filenames never collide: same beat/customer/date appends `_2`, `_3`, …

## License tiers (Presets)
Seed tiers (price lives in the sale form, never in the tier):

| Tier | Kind | Term | Files | Royalty | Publishing | Caps |
|---|---|---|---|---|---|---|
| MP3 / WAV / Trackout / Unlimited Lease | non-exclusive | 10y | tier bundle | 0% | Producer retains 100% | 5000 / 500000 |
| Exclusive | exclusive | 10y | WAV + stems | 3% | 50/50 | unlimited |

Duplicate a tier, or duplicate tier + template (copies the contract text so edits never
touch the original). A tier whose template file is missing shows `[missing]` instead of
silently switching contracts. Tiers used by saved sales cannot be deleted (history is WORM).

## Contract templates
Four bundled seeds in `app/seed_templates/` (read-only; edits use copy-on-write to
`<data>/templates/`, Reset restores the bundled text):

| File | Sections | Use |
|---|---|---|
| `non_exclusive_lease.md` / `_ES.md` | 25 | WAV/MP3/Trackout/Unlimited tiers |
| `exclusive_10y.md` / `_ES.md` | 25 | Exclusive tier |

Both are full-length contracts: parties, ownership (no copyright transfer), grant, catalog
status / exclusivity, master recording, distribution + caps + upgrade path, Content ID rules
(prohibited on leases, allowed for the exclusive holder's own release), sync rules, live/broadcast,
credit (`Prod. by …`), term + expiration, publishing, master royalty (net receipts defined),
consideration, breach/termination, no refunds, delivery, third-party samples, restrictions,
non-transferability, representations, indemnification, entire agreement, governing law,
purchase + payment = acceptance. `_ES` files are the Spanish mirror (English prevails unless
agreed otherwise).

## Variables
`{VAR}` (BeatStars) and `{{var}}` (TRAKK, case-insensitive) + single-level
`{IF KEY}…{ENDIF}` blocks. Price is composed from amount + currency
(`PRODUCT_PRICE`, auto `PRODUCT_PRICE_WORD` via `money_to_words`, incl. cents).
`TERM_START` defaults to the effective date, `TERM_END` to start + years,
`COUNTRY` to the last segment of `State, Country`. Every known variable defaults to `""`,
so known keys never print literally; unknown keys warn on template save.

### IPI identifiers (optional)
`{PRODUCER_IPI}` / `{CUSTOMER_IPI}` (Interested Party Information, the 9–11 digit CISAC
identifier that links each party to its PRO — SACM, BMI, ASCAP — for royalty identification):

- **Your IPI → Settings > Producer profile** (`profile_producer_ipi`). Fill it once; every
  sale autofills it and opts the license in automatically.
- **Customer IPI → Generator > "IPI identifiers (optional)" checkbox group.** Off = both
  blank (contract lines hidden). On = both inputs revealed. The buyer's IPI is often unknown —
  leave it blank, the contract stays clean.
- Templates render IPI lines only when filled (`{IF}` blocks). A malformed value only warns
  in the status bar (`… format? (IPI is 9-11 digits)`) — sales are never blocked by it.
  Leading zeros are preserved. Present IPIs are also appended to the PDF cover rows and
  persisted per sale (`producer_ipi` / `customer_ipi` columns + full text hash).

## Settings profile (autofill)
Settings > Producer profile: alias, owner fullname, **producer IPI**, location, state/country.
Empty sale-form fields autofill from the profile; typed values are respected. Document brand (explicit `brand_name` → sale-form producer alias → profile alias → TRAKKLICENSE):
cover eyebrow (`{brand} — Beat License`), cover footer and every-page footer. The licensor
named in each contract governs its brand. Filenames keep using `filename_prefix`
(file organization, separate concern).
Other settings:
output folder, filename prefix/hash/folio toggles, folio on/off, PDF cover, open-after-export,
evidence footer, page size LETTER/A4, default language/currency, acceptance-checkbox requirement.

## Data locations
- Running from source: `%APPDATA%\TRAKKLICENSE\` (`trakklicense.db`, `out\`, `templates\`, `settings.json`).
- Frozen `.exe`: portable `data\` next to the exe. Override anywhere with `TRAKKLICENSE_DATA_DIR`.
- Never commit `data/*.db`, `out/*`, `.venv/`, real customer data. Seed templates must contain
  no personal data (tests scan for it).

## Tests & quality gates
```bat
.venv\Scripts\python -m pytest tests -q                                   :: full suite + coverage (gate ≥80%)
.venv\Scripts\python -m pytest tests -q -p no:cacheprovider --no-cov -m "not slow"   :: fast loop
.venv\Scripts\python tools\quality_metrics.py                             :: gates → data\quality_report.json
```
Gates (`QUALITY_METRICS.md`, procedures in `QA.md`): 100% pass rate, ≥80% coverage,
7/7 Gherkin scenarios (`features/*.feature`), PDF export smoke (>500B), template no-leak scan.

## Build the .exe
```
py build_exe.py              :: tests + windowed one-file exe (~60 MB, bundles styles.qss + seeds)
py build_exe.py --console    :: console build for diagnostics
py build_exe.py --skip-tests :: skip pytest (not recommended)
```

## Distribution
Portable: copy `dist\TRAKKLICENSE.exe` anywhere (no installer needed — offline app,
no third-party binaries, no admin rights). First launch creates `data\` next to it
(DB, Reexports, settings). No installer is shipped (see MAINTENANCE for the rationale).

## Version
Single source: `app/version.py` (`__version__`, shown in the window title + Help > About).
`pyproject.toml` and `build_exe.py` read it — bump it there per release.

## Project layout
```
main.py                  :: entry (QApplication + global QSS + MainWindow maximized)
app/engine/              :: renderer ({VAR}/{{var}}/{IF}), variables catalog, validators, money_words
app/database/            :: SQLite (WAL) connection + migrations, repositories, seed (5 tiers)
app/services/            :: generation, sale (folio+re-render+persist), export (MD/PDF),
                            document (filenames/footer/cover), templates (bundled+user),
                            settings (JSON + atomic folio counter)
app/ui/                  :: MainWindow coordinator + shell menus + 4 views
                            (Generator/History/Presets/Templates) + dialogs + styles.qss
app/seed_templates/      :: 4 bundled contracts (EN+ES × non-exclusive+exclusive)
app/utils/paths.py       :: base/db/out/templates dirs (portable + frozen aware)
features/ + tests/       :: Gherkin scenarios + unit/regression/GUI tests
tools/quality_metrics.py :: gates runner
```

## Legal Disclaimer — please read before using

**1. Not legal advice, not a law firm.** TRAKKLICENSE is a self-help document-automation
tool created by an independent beatmaker, not a law firm. No attorney-client relationship
is created by downloading, installing, or using this software, and communications through
it are not protected by attorney-client privilege. Nothing here is legal advice, a legal
opinion, or a recommendation about your rights, options, choice of license, or strategy.

**2. General information only.** Templates are provided as general information on issues
commonly encountered when licensing beats. The law changes constantly, differs from
jurisdiction to jurisdiction, and is subject to interpretation by different courts. No
template can fit every circumstance. Information and templates are not guaranteed to be
correct, complete, or up to date.

**3. Self-help at your direction.** The software only fills in the values you type into the
templates you select. At no time does it review your answers for legal sufficiency, draw
legal conclusions, or apply the law to the facts of your situation. You represent yourself
in every legal matter you handle with this tool.

**4. Use at your own risk and under your own judgment ("as is").** The software and the
templates are provided "AS IS", without warranty of any kind, express or implied, including
but not limited to warranties of performance, merchantability, fitness for a particular
purpose, and non-infringement. There is no guarantee of completeness, accuracy, timeliness,
or of any result obtained from using them. Any decision made or action taken in reliance on
a generated document is exclusively yours.

**5. Final responsibility lies with you, the end user.** Before selling, signing, or
delivering any license you must, on your own responsibility: (a) verify the terms with a
licensed attorney in your jurisdiction, especially for exclusive deals, high-value sales,
or cross-border transactions; (b) confirm you own or control every right you license and
have cleared every third-party sample, loop, or interpolation (or disclose it); (c) confirm
the other party has legal capacity (age 18+ or guardian consent); (d) register your shares
with your PRO / publisher (e.g. SACM, BMI, ASCAP) so they match the contract; (e) handle
applicable taxes and payment proof yourself.

**6. Limitation of liability.** To the maximum extent permitted by applicable law, in no
event shall the authors or copyright holders be liable for any claim, damages, or other
liability — whether special, direct, indirect, incidental, or consequential (including loss
of goodwill, work stoppage, lost royalties, or any commercial loss) — arising from, out of,
or in connection with the software, the templates, or any generated document, even if advised
of the possibility of such damages. If you need legal advice for your specific situation, or
your matter is too complex for a self-help tool, consult a licensed attorney in your area.

---
### Aviso legal (resumen en español)

TRAKKLICENSE es solo una herramienta de autoayuda para rellenar plantillas: no es un
despacho, no da asesoría legal y no crea relación abogado-cliente. Úsala bajo tu propio
criterio y riesgo ("as is", sin garantías). La responsabilidad final es 100% del usuario:
verifica cada contrato con un abogado de tu jurisdicción, asegura que tienes los derechos
que licencias, declara tus samples, y registra tus regalías en tu PRO. Los autores no
responden por reclamos, daños ni pérdidas derivados de su uso.
