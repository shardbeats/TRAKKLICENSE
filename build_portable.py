#!/usr/bin/env python3
"""Build the portable TRAKKLICENSE (one-dir inside a ZIP).

One-dir starts instantly: nothing is extracted on launch. The portable is
shipped as a ZIP the user unzips once:

    dist\\TRAKKLICENSE-portable-<version>.zip
        TRAKKLICENSE\\
            TRAKKLICENSE.exe
            _internal\\   (Qt, styles.qss, seed_templates, ...)
            README.md / LICENSE / NOTICE.md / THIRD-PARTY-NOTICES.md

Usage:
  python build_portable.py              # tests + windowed onedir + ZIP
  python build_portable.py --console    # console build for diagnostics
  python build_portable.py --skip-tests # skip pytest (not recommended)

The old `build_exe.py` produced a one-file exe that re-extracted the payload
to %TMP% on EVERY launch; it was removed on purpose.
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "TRAKKLICENSE"
ICON_NAME = "icon.ico"
EXE_DIR = ROOT / "dist" / "portable" / APP_NAME
DOCS = ("README.md", "LICENSE", "NOTICE.md", "THIRD-PARTY-NOTICES.md")
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def build_python() -> str:
    """Prefer the project venv (has pytest + deps); fall back to the runner."""
    if VENV_PY.is_file():
        return str(VENV_PY)
    print(f"WARNING: {VENV_PY} not found — using {sys.executable} "
          "(run start.bat first for the full environment).")
    return sys.executable


def project_version() -> str:
    """Single source: app/version.py (regex, no import needed)."""
    text = (ROOT / "app" / "version.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("ERROR: version not found in app/version.py")
    return m.group(1)


def ensure_pytest(python: str) -> bool:
    """Fresh venvs (start.bat) only install requirements.txt (app deps)."""
    probe = subprocess.run([python, "-m", "pytest", "--version"],
                           capture_output=True, cwd=ROOT)
    if probe.returncode == 0:
        return True
    print("pytest not found. Installing requirements-dev.txt...")
    dev = ROOT / "requirements-dev.txt"
    if not dev.is_file():
        print(f"ERROR: {dev.name} missing, cannot install pytest.")
        return False
    r = subprocess.run([python, "-m", "pip", "install", "-r", str(dev)], cwd=ROOT)
    return r.returncode == 0


def run_tests() -> int:
    print("[1/2] Running pytest...")
    python = build_python()
    if not ensure_pytest(python):
        print("ERROR: could not install pytest, aborting build.")
        return 1
    r = subprocess.run([python, "-m", "pytest", "tests", "-q"], cwd=ROOT)
    return r.returncode


def main() -> int:
    args = set(sys.argv[1:])
    version = project_version()
    print(f"{APP_NAME} version: {version}")
    if "--skip-tests" not in args:
        if run_tests() != 0:
            print("ERROR: tests failed, aborting build.")
            return 1
    else:
        print("[1/2] Skipping tests (--skip-tests).")

    python = build_python()
    try:
        subprocess.run([python, "-m", "PyInstaller", "--version"],
                       check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not installed. Installing...")
        subprocess.run([python, "-m", "pip", "install", "pyinstaller"], check=True)

    sep = os.pathsep  # ";" only on Windows — keeps Linux/macOS builds working.
    windowed = [] if "--console" in args else ["--windowed"]
    cmd = [
        python, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir",
        *windowed,
        "--name", APP_NAME,
        "--distpath", "dist/portable",
        "--workpath", "build/portable",
        "--specpath", "build/portable",
        "--add-data", f"{ROOT / 'app' / 'ui' / 'styles.qss'}{sep}app/ui",
        "--add-data", f"{ROOT / 'app' / 'seed_templates'}{sep}app/seed_templates",
    ]
    icon = ROOT / ICON_NAME
    if icon.exists():
        cmd += ["--icon", str(icon), "--add-data", f"{icon}{sep}."]
        print(f"  Icon: {icon}")
    else:
        print("  WARNING: no icon.ico, using default PyInstaller icon.")

    cmd.append(str(ROOT / "main.py"))
    if EXE_DIR.exists():
        shutil.rmtree(EXE_DIR, ignore_errors=True)
    print("[2/2] Running PyInstaller...")
    print("  " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)

    exe = EXE_DIR / f"{APP_NAME}.exe"
    if not exe.is_file():
        print("ERROR: exe not found in dist/portable/")
        return 1

    for name in DOCS:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, EXE_DIR / name)

    out = ROOT / "dist" / f"{APP_NAME}-portable-{version}.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(EXE_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, Path(APP_NAME) / p.relative_to(EXE_DIR))

    print(f"BUILD OK: {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"Unzip once, then run {APP_NAME}\\{APP_NAME}.exe "
          "(first launch creates data/ next to it).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
