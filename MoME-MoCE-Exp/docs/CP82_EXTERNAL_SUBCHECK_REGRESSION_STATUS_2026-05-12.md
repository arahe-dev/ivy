# CP82 External Subcheck Regression Status - 2026-05-12

CP82 makes the combined regression gate expose every external sub-gate check.

Before CP82, the combined gate failed if the external gate failed, but the top-level `checks` table mostly showed a coarse `external_generalization_all_pass` result plus a few baseline precision checks. That made the pass/fail surface less diagnosable than the external gate itself.

## What Changed

- `scripts/run_context_memory_regression_gate.py` now imports `external["status"]["checks"]`.
- Each external subcheck is added to the combined gate with an `external_` prefix.
- `tests/test_context_memory_regression_gate.py` verifies that external subchecks are included and can fail the combined gate.

## Covered Subchecks

The combined regression gate now exposes detailed checks for:

- external baseline
- no-exact-anchor ablation
- semantic paraphrase ablation
- semantic plus no-exact ablation
- negative controls
- source-removal sensitivity
- semantic source-removal sensitivity
- latency budgets for each surface

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_cp21_cp24_cp23_contract.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- Focused pytest subset: `9 passed`.
- Combined regression gate: `passed`.
- Combined status now includes detailed `external_*` checks.
