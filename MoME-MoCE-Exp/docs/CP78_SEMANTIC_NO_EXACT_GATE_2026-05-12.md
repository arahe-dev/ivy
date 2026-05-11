# CP78 Semantic Plus No-Exact Gate - 2026-05-12

CP78 combines the CP76 and CP77 pressure tests.

The external Signal/Recall pack now runs a fourth default surface: hand-paraphrased queries with `exact_anchor_memory` disabled. This is stronger than testing paraphrases and exact-anchor removal separately.

## What Changed

- `scripts/run_external_generalization_gate.py` now runs `semantic_no_exact_anchor_ablation` by default.
- `scripts/run_context_memory_regression_gate.py` reports the combined ablation.
- Focused tests verify the combined ablation is present and passes.

## Combined Gate Result

| Run | Passed | Required Precision | Forbidden Hits | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|---:|
| External baseline | `9 / 9` | `1.0` | `0` | `0.411 ms` | `0.596 ms` |
| No exact anchor | `9 / 9` | `1.0` | `0` | `0.376 ms` | `0.500 ms` |
| Semantic paraphrase | `9 / 9` | `1.0` | `0` | `0.409 ms` | `0.586 ms` |
| Semantic + no exact anchor | `9 / 9` | `1.0` | `0` | `0.416 ms` | `0.597 ms` |

## Interpretation

This makes the external gate less vulnerable to two benchmark-shape objections at the same time:

- The exact-anchor expert is not required.
- The original query wording is not required.

The benchmark is still small and hand-authored, but CP78 is a stronger credibility guard than the earlier one-off CP23 external run.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp78_external_semantic_no_exact_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- External gate: `passed`.
- Semantic + no-exact-anchor ablation: `9 / 9`.
- Focused pytest subset: `9 passed`.
- Combined regression gate: `passed`.
