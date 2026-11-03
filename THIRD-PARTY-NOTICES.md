# THIRD-PARTY-NOTICES — TRAKKLICENSE

TRAKKLICENSE code is MIT (`LICENSE`). The components below keep
their own licenses, in source runs AND inside the frozen exe.

| Component | License | Notes |
|---|---|---|
| PySide6 + Qt | LGPLv3 | GUI toolkit. https://www.qt.io + https://pypi.org/project/PySide6/ |
| reportlab | BSD-3-Clause | PDF generation. https://www.reportlab.com/ |
| Python stdlib (sqlite3) | PSF | Local DB (no customer data committed). |

Template/content note: contract templates shipped in
`app/seed_templates/` are part of the MIT code as document
automation samples — they are not legal advice (see README).

Build tool only: PyInstaller (GPLv2 with bootloader exception),
pytest/pytest-bdd (MIT, dev only).

Compliance: ship `LICENSE` + `NOTICE.md` + this file with the app;
LGPL/BSD texts via the links above.
