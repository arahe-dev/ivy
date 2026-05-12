# CP75 External Guard In Regression Gate - 2026-05-12

CP75 wires the CP74 Signal/Recall external generalization gate into the combined context-memory regression gate.

This makes non-IVY generalization a default regression concern instead of an optional side report.

## What Changed

- `scripts/run_context_memory_regression_gate.py` now runs the external generalization gate by default.
- The external guard can be skipped only with `--skip-external-generalization`.
- The regression report now includes external pass count, required precision, forbidden hits, mean latency, p95 latency, and per-case selected evidence.
- `tests/test_context_memory_regression_gate.py` now verifies the external checks and report section.

## Combined Gate Result

| Gate | Result |
|---|---:|
| Mined policy pass | `5 / 5` |
| Feature eval pass | `5 / 5` |
| Plugin benchmark pass | `6 / 6` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.442 ms` |
| External p95 latency | `0.708 ms` |
| Gate status | `passed` |

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe -m pytest tests\test_context_memory_regression_gate.py tests\test_cp21_cp24_cp23_contract.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- Regression gate: `passed`.
- Pytest subset: `9 passed`.
