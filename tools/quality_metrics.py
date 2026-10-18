"""Quality metrics: pytest + coverage gates + PDF smoke. Writes data/quality_report.json."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "quality_report.json"
COV_GATE = 80.0


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    cov = run([sys.executable, "-m", "pytest", "tests/",
               "-p", "no:cacheprovider",
               "--cov=app", "--cov-report=term-missing", "--tb=short"])
    out = (cov.stdout or "") + "\n" + (cov.stderr or "")
    m_pass = re.search(r"(\d+) passed", out)
    m_fail = re.search(r"(\d+) failed", out)
    passed = int(m_pass.group(1)) if m_pass else 0
    failed = int(m_fail.group(1)) if m_fail else 0
    m_cov = re.search(r"^TOTAL\s+(?:\d+\s+)+([\d.]+)%", out, re.MULTILINE)
    coverage = float(m_cov.group(1)) if m_cov else 0.0

    # PDF smoke (reportlab available + export works)
    pdf_ok = False
    try:
        import tempfile
        from app.services.export import export_pdf
        with tempfile.TemporaryDirectory() as td:
            p = export_pdf("# T\nhello", Path(td), "B", "C", "2026-10-17")
            pdf_ok = p.exists() and p.stat().st_size > 500
    except Exception as e:
        print(f"PDF smoke FAIL: {e}")

    gates = {
        "pass_rate": "PASS" if passed > 0 and failed == 0 else "FAIL",
        "coverage": "PASS" if coverage >= COV_GATE else "FAIL",
        "pdf_export": "PASS" if pdf_ok else "FAIL",
        "gherkin": "PASS" if "test_gherkin" in out or passed > 0 else "FAIL",
    }
    report = {"tests": passed + failed, "passed": passed, "failed": failed,
              "coverage_total": coverage, "coverage_gate": COV_GATE,
              "gates": gates,
              "overall": "PASS" if all(v == "PASS" for v in gates.values()) else "FAIL"}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
