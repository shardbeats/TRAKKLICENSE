#!/usr/bin/env python3
"""Build a portable one-file .exe for TRAKKLICENSE (PyInstaller).

Bundles styles.qss + seed_templates.
Usage:
  python build_exe.py              # tests + windowed exe (~60 MB)
  python build_exe.py --console    # console build for diagnostics
  python build_exe.py --skip-tests # skip pytest (not recommended)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "TRAKKLICENSE"
ICON_NAME = "icon.ico"
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
    """Fresh venvs (start.bat) only install requirements.txt (app deps).

    pytest lives in requirements-dev.txt, so a fresh clone has no pytest.
    Install dev deps on demand instead of failing the build.
    """
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
    print(f"{APP_NAME} version: {project_version()}")
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

    import os
    sep = os.pathsep  # FIX: ";" only works on Windows — os.pathsep keeps Linux/macOS builds working.
    windowed = [] if "--console" in args else ["--windowed"]
    cmd = [
        python, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile",
        *windowed,
        "--name", APP_NAME,
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
    print("[2/2] Running PyInstaller...")
    print("  " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)

    exe = ROOT / "dist" / f"{APP_NAME}.exe"
    if exe.exists():
        print(f"BUILD OK: {exe} ({exe.stat().st_size/1024/1024:.1f} MB)")
        print("Portable: copy the .exe anywhere. First launch creates data/ next to it or %APPDATA%/TRAKKLICENSE.")
        return 0
    print("ERROR: exe not found in dist/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
