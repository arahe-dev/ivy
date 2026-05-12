# CP79 External Negative-Control Gate - 2026-05-12

CP79 adds near-miss negative controls to the external Signal/Recall gate.

The prior external gates proved the router could retrieve the right evidence under paraphrase and exact-anchor ablation. CP79 tests the opposite failure mode: questions that mention known products but ask for unsupported current/product facts. These should abstain instead of selecting adjacent identity or architecture notes.

## Initial Failure

Before the fix, the dry-run negative controls passed only `1 / 5`.

| Case | Bad Behavior |
|---|---|
| Signal Android Play Store release version | selected `external_signal_local_first_protocol` |
| Signal hosted uptime SLA | selected `external_signal_not_cloud_service` |
| Recall production iOS app ship date | selected `external_recall_board_identity` |
| Recall SOC 2 certification | selected `external_recall_board_identity` |

Only Recall Cloud pricing abstained correctly.

## What Changed

- Tightened `query_requests_unsupported_commercial_fact(...)` for release versions, app-store status, hosted SLAs, ship dates, and certifications.
- Tightened `_supports_current_commercial_fact(...)` so related identity notes are not enough for current commercial/product-status claims.
- Added `negative_control_ablation` to `scripts/run_external_generalization_gate.py`.
- Added the negative controls to the combined regression report.
- Focused tests assert negative controls pass with `avg_selected == 0.0`.

## Combined Gate Result

| Run | Passed | Avg Selected | Mean Latency | P95 Latency |
|---|---:|---:|---:|---:|
| External negative controls | `5 / 5` | `0.0` | `0.504 ms` | `0.674 ms` |

## Negative Controls

| Case | Expected |
|---|---|
| Latest Android Play Store release version for Signal bridge | abstain |
| Hosted uptime SLA for Signal customers | abstain |
| Current monthly subscription price for Recall Cloud | abstain |
| Recall Board production iOS app ship date | abstain |
| Current SOC 2 certification for Recall Board | abstain |

## Interpretation

This improves precision in the practical sense: the router now refuses plausible-but-unsupported current facts even when related product evidence exists. That matters more for final-answer quality than another easy positive retrieval case, because these are the kinds of adjacent facts that make agents hallucinate.

## Verification

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\mome_moce_harness.py scripts\run_external_generalization_gate.py scripts\run_context_memory_regression_gate.py
.\.venv\Scripts\python.exe scripts\run_external_generalization_gate.py --json-out out\cp79_external_negative_control_gate.json
.\.venv\Scripts\python.exe -m pytest tests\test_cp21_cp24_cp23_contract.py tests\test_context_memory_regression_gate.py -q
.\.venv\Scripts\python.exe scripts\run_context_memory_regression_gate.py
```

Result:

- External negative controls: `5 / 5`.
- Negative-control avg selected: `0.0`.
- Focused pytest subset: `9 passed`.
- Combined regression gate: `passed`.
