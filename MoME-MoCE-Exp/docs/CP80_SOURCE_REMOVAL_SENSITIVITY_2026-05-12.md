# CP80 Source-Removal Sensitivity - 2026-05-12

CP80 adds source-removal sensitivity to the external Signal/Recall gate.

This addresses a benchmark validity concern: if the required source is removed, the router should not still pass by selecting adjacent evidence. Before the fix, it often did.

## Initial Failure

Removing the required source from each answerable external case initially produced only `1 / 8` abstentions. After a first specificity pass it improved to `5 / 8`, then `7 / 8`. The final fix reached `8 / 8`.

Examples of bad pre-fix behavior:

| Case | Removed Required Source | Bad Selection |
|---|---|---|
| `cp23_signal_iphone_without_vps` | `external_signal_tailscale_webpush` | `external_recall_ai_context` |
| `cp23_signal_not_codex_cloud` | `external_signal_not_cloud_service` | `external_signal_local_first_protocol` |
| `cp23_signal_daemon_shell_boundary` | `external_signal_worker_boundary` | `external_signal_context_artifacts` |
| `cp23_recall_graph_ir_role` | `external_recall_graph_ir` | `external_recall_ai_context` |

## What Changed

- Added `_supports_query_specificity(...)` to the deterministic router.
- Specific external queries now require evidence that actually supports the requested subclaim:
  - iOS/private delivery needs iPhone/Web Push/Tailscale/VPS evidence.
  - Signal cloud/Codex identity needs explicit cloud/Codex/broker evidence.
  - durable coordination needs event-log/SQLite/source-of-truth evidence.
  - daemon shell boundary needs daemon-specific evidence.
  - Recall screenshot-free AI context needs structured board-context/board-facts evidence.
  - Recall text graph, Graph IR, and second-brain queries require matching subclaim terms.
- Added `source_removal_ablation` to `scripts/run_external_generalization_gate.py`.
- Added source-removal output to the combined regression report.

## Combined Gate Result

| Run | Passed | Avg Selected | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|
| External source-removal sensitivity | `8 / 8` | `0.0` | `0.384 ms` | `0.539 ms` |

## Interpretation

CP80 is a stronger benchmark-validity check than another positive retrieval case. It verifies that required labels are causal: when the required source disappears, the router abstains instead of laundering nearby evidence into a plausible answer.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\mome_moce_harness.py scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp80_external_source_removal_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- External source-removal sensitivity: `8 / 8`.
- Source-removal avg selected: `0.0`.
- Focused pytest subset: `9 passed`.
- CP26 external-ingester smoke: `passed`.
- Combined regression gate: `passed`.
