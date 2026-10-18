"""App paths: portable <exe>/data else %APPDATA%/TRAKKLICENSE. No personal data."""
import os
import sys
from pathlib import Path


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    override = os.environ.get("TRAKKLICENSE_DATA_DIR")
    if override:
        return Path(override)
    # FIX (PyInstaller onefile): __file__ lives in _MEI temp, not next to the
    # .exe — data must live next to sys.executable so it survives restarts.
    if _frozen():
        return Path(sys.executable).resolve().parent / "data"
    # portable next to exe/script
    here = Path(__file__).resolve().parents[2]
    portable = here / "data"
    # if running from source, prefer APPDATA
    appdata = os.environ.get("APPDATA")
    if (here / "app").exists() and appdata:
        return Path(appdata) / "TRAKKLICENSE"
    return portable


def db_path() -> Path:
    return base_dir() / "trakklicense.db"


def out_dir() -> Path:
    d = base_dir() / "out"
    d.mkdir(parents=True, exist_ok=True)
    return d


def templates_dir() -> Path:
    # FIX (PyInstaller): bundled seeds live in _MEIPASS/app/seed_templates
    # (--add-data app/seed_templates;app/seed_templates). Prefer it when frozen.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = Path(meipass) / "app" / "seed_templates"
        if cand.is_dir():
            return cand
    return Path(__file__).resolve().parents[1] / "seed_templates"


def styles_path() -> Path:
    """QSS location that also works inside the frozen .exe."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = Path(meipass) / "app" / "ui" / "styles.qss"
        if cand.is_file():
            return cand
    return Path(__file__).resolve().parents[1] / "ui" / "styles.qss"
