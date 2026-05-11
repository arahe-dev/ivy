# CP77 Semantic Paraphrase Gate - 2026-05-12

CP77 adds a semantic-paraphrase ablation to the external Signal/Recall generalization gate.

CP76 showed the external pack does not rely solely on `exact_anchor_memory`, but the queries still resembled the original wording. CP77 reruns the same labels with hand-paraphrased user questions that avoid copying the original query text while preserving the expected evidence contract.

## What Changed

- `scripts/run_external_generalization_gate.py` now includes `SEMANTIC_PARAPHRASES`.
- The external gate runs baseline, no-exact-anchor, and semantic-paraphrase evaluations by default.
- `scripts/run_context_memory_regression_gate.py` reports semantic-paraphrase results in the combined gate.
- Focused tests assert the semantic-paraphrase ablation passes and appears in the regression report.

## Combined Gate Result

| Run | Passed | Required Precision | Forbidden Hits | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|---:|
| External baseline | `9 / 9` | `1.0` | `0` | `0.424 ms` | `0.598 ms` |
| No exact anchor | `9 / 9` | `1.0` | `0` | `0.451 ms` | `0.682 ms` |
| Semantic paraphrase | `9 / 9` | `1.0` | `0` | `0.497 ms` | `0.813 ms` |

## Example Paraphrases

| Original Case | Paraphrased Query |
|---|---|
| `cp23_signal_iphone_without_vps` | For the Signal phone bridge, what private delivery path reaches iOS without renting a public server? |
| `cp23_signal_daemon_shell_boundary` | In Signal, should the notification daemon itself run arbitrary shell work from a phone response? |
| `cp23_recall_screenshot_free_context` | In Recall Board, what machine-readable export lets an AI inspect a board without screenshots? |
| `cp23_recall_cloud_price_abstain` | What is the current subscription price for Recall Cloud? |

## Interpretation

This is still not a natural user traffic benchmark, and it still uses product names where that is required to identify the external project. It is stronger than CP76 because it changes the phrasing while keeping expected evidence stable. The deterministic router continues to select the right source or abstain, with sub-millisecond p95 latency for the paraphrase set in the latest combined gate.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp77_external_semantic_paraphrase_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- External gate: `passed`.
- Semantic paraphrase ablation: `9 / 9`.
- Focused pytest subset: `9 passed`.
- Combined regression gate: `passed`.
