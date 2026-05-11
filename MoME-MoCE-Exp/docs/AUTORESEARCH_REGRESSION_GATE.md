# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T19:07:37Z`
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
| Mined policy avg wall | `27.801 ms` |
| Feature profile winner | `baseline` |
| Feature pass | `5 / 5` |
| Feature avg wall | `30.586 ms` |
| Feature avg router | `1.982 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `17.686 ms` |
| Plugin avg router | `2.652 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.424 ms` |
| External p95 latency | `0.598 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.451 ms` |
| External no-exact-anchor p95 latency | `0.682 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.497 ms` |
| External semantic-paraphrase p95 latency | `0.813 ms` |

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
| baseline | 5 / 5 | 30.586 | 1.982 |
| checkpoint_guard | 5 / 5 | 21.496 | 2.013 |
| code_penalty | 5 / 5 | 21.805 | 2.115 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 27.801 | 2.325 |
| 16 | 4 / 5 | 17.736 | 1.344 |
| 64 | 4 / 5 | 31.001 | 4.199 |
| 128 | 4 / 5 | 40.227 | 7.116 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.606` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.378` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.586` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.426` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.371` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.388` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.334` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.237` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.49` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.586` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.385` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.552` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.387` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.357` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.746` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.336` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.232` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.475` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.495` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.522` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.598` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.325` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.423` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.443` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.433` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.281` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.956` |
