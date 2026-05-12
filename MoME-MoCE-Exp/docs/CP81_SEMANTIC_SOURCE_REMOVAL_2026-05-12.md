# CP81 Semantic Source-Removal Sensitivity - 2026-05-12

CP81 extends CP80 by applying source-removal sensitivity to the semantic paraphrase queries.

CP80 proved that removing the required source makes the original external queries abstain. CP81 checks the stronger condition: remove the required source and change the query wording. The router should still abstain instead of selecting adjacent evidence.

## Initial Finding

The first dry run passed `7 / 8`.

The remaining leak was:

| Case | Removed Required Source | Bad Selection |
|---|---|---|
| `cp23_recall_text_graph_contents` semantic paraphrase | `external_recall_text_graph` | `external_recall_graph_ir` |

The paraphrase asked for a "compact graph representation" from visible board structure, so the prior text-graph specificity trigger did not fire because it only looked for the literal phrase `text graph`.

## What Changed

- Broadened the Recall text-graph specificity trigger to include:
  - `compact graph representation`
  - `visible board structure`
  - `board structure`
- Kept the support requirement specific to text-graph contents: nodes, edges, groups, annotations, or unresolved relationships.
- Added `semantic_source_removal_ablation` to `scripts/run_external_generalization_gate.py`.
- Added semantic source-removal output to the combined regression report.

## Combined Gate Result

| Run | Passed | Avg Selected | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|
| External semantic source-removal | `8 / 8` | `0.0` | `0.416 ms` | `0.623 ms` |

## Interpretation

This closes another benchmark-shape escape hatch. The external gate now verifies required-source causality for both original and paraphrased questions, so adjacent evidence cannot pass simply because it shares project vocabulary.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\mome_moce_harness.py scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp81_external_semantic_source_removal_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py tests\test_cp26_cp28_contract.py::test_cp26_external_ingester_routes_smoke_cases -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- Semantic source-removal sensitivity: `8 / 8`.
- Semantic source-removal avg selected: `0.0`.
- Focused pytest subset: `10 passed`.
- Combined regression gate: `passed`.
