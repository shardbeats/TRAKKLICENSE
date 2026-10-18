# QUALITY METRICS — TRAKKLICENSE

Gates via `py tools\quality_metrics.py` → `data/quality_report.json`.

| Metric | Gate | How measured | Why here |
|---|---|---|---|
| Test pass rate | 100% | `pytest tests/ -q` | Broken render = invalid contract |
| Total coverage | ≥80% | `--cov=app --cov-fail-under=80` | Forces engine/db/services coverage |
| Gherkin scenarios | 7/7 green | `tests/test_gherkin.py` | Business contracts always alive |
| PDF export smoke | PASS | export 1-page PDF >500B | The PDF is the product |
| Template no-leak | 0 forbidden | `test_templates_qa.py` FORBIDDEN scan | No real personal data in repo |
| PDF QC | 4/4 checks | `QA.md` §5 manual | Final PDF must open clean |

Example report:
```json
{"tests": 25, "passed": 25, "coverage_total": 86.0, "gates": {"pass_rate": "PASS", "coverage": "PASS"}}
```
