# CP76 Exact Anchor Ablation - 2026-05-12

CP76 adds an exact-anchor ablation to the external Signal/Recall generalization gate.

This directly tests the concern that exact anchor routing makes the task trivial. The same external cases are rerun with `exact_anchor_memory` disabled. The gate now fails unless both the normal run and the no-exact-anchor run pass.

## What Changed

- `scripts/run_external_generalization_gate.py` now runs a default no-exact-anchor ablation.
- `scripts/run_context_memory_regression_gate.py` includes the ablation result in the combined report because CP75 runs the external gate by default.
- `tests/test_cp21_cp24_cp23_contract.py` verifies the ablation passes.
- `tests/test_context_memory_regression_gate.py` verifies the combined report includes the ablation section.

## Result

| Run | Passed | Required Precision | Forbidden Hits | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|---:|
| External baseline | `9 / 9` | `1.0` | `0` | `0.383 ms` | `0.564 ms` |
| No exact anchor | `9 / 9` | `1.0` | `0` | `0.383 ms` | `0.501 ms` |

## Interpretation

The external gate still uses recognizable product vocabulary such as Signal and Recall, so this is not a semantic paraphrase benchmark. It does show that the result is not solely caused by the `exact_anchor_memory` expert. Sparse lexical evidence, source-family cues, authority gates, decoy rejection, and abstention policy are enough to pass this external pack without exact-anchor activation.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp76_external_no_exact_anchor_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- External baseline: `9 / 9`.
- No-exact-anchor ablation: `9 / 9`.
- Focused pytest subset: `9 passed`.
- Combined regression gate: `passed`.
