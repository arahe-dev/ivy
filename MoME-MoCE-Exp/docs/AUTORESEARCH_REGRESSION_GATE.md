# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T18:44:30Z`
Gate passed: `True`
Mined/feature router budget: `5.0 ms`
Full plugin router budget: `15.0 ms`
Mined/feature wall budget: `35.0 ms`
Full plugin wall budget: `25.0 ms`

## Summary

| Gate | Result |
|---|---:|
| Mined policy winner | `max_prefilter_items=32` |
| Mined policy pass | `5 / 5` |
| Mined policy avg wall | `24.569 ms` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg wall | `26.392 ms` |
| Feature avg router | `2.163 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `18.108 ms` |
| Plugin avg router | `2.681 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.442 ms` |
| External p95 latency | `0.708 ms` |

## Checks

| Check | Pass |
|---|---:|
| `mined_policy_all_pass` | `True` |
| `feature_eval_all_pass` | `True` |
| `plugin_benchmark_all_pass` | `True` |
| `feature_router_under_budget` | `True` |
| `plugin_router_under_budget` | `True` |
| `mined_policy_wall_under_budget` | `True` |
| `feature_wall_under_budget` | `True` |
| `plugin_wall_under_budget` | `True` |
| `external_generalization_all_pass` | `True` |
| `external_generalization_required_recall` | `True` |
| `external_generalization_required_precision` | `True` |
| `external_generalization_no_forbidden_hits` | `True` |

## Feature Profiles

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| checkpoint_guard | 5 / 5 | 26.392 | 2.163 |
| baseline | 5 / 5 | 32.466 | 2.246 |
| code_penalty | 5 / 5 | 24.193 | 2.367 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 24.569 | 2.103 |
| 16 | 4 / 5 | 23.506 | 1.272 |
| 64 | 4 / 5 | 28.841 | 3.768 |
| 128 | 4 / 5 | 40.46 | 7.39 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.783` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.421` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.596` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.404` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.361` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.34` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.343` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.234` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.497` |
