# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T18:53:06Z`
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
| Mined policy avg wall | `25.547 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `21.714 ms` |
| Feature avg router | `2.115 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `15.217 ms` |
| Plugin avg router | `2.45 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.383 ms` |
| External p95 latency | `0.564 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.383 ms` |
| External no-exact-anchor p95 latency | `0.501 ms` |

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
| code_penalty | 5 / 5 | 21.714 | 2.115 |
| checkpoint_guard | 5 / 5 | 23.495 | 2.264 |
| baseline | 5 / 5 | 35.894 | 2.271 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 25.547 | 2.068 |
| 16 | 4 / 5 | 18.326 | 1.2 |
| 64 | 4 / 5 | 30.018 | 4.034 |
| 128 | 4 / 5 | 48.793 | 8.225 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.536` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.371` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.583` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.356` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.34` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.313` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.311` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.209` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.431` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.444` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.358` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.531` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.358` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.357` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.433` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.309` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.196` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.457` |
