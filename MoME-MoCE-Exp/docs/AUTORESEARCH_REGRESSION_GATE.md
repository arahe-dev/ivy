# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T19:22:15Z`
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
| Mined policy avg wall | `24.866 ms` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg wall | `21.968 ms` |
| Feature avg router | `2.148 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `14.868 ms` |
| Plugin avg router | `2.295 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.411 ms` |
| External p95 latency | `0.596 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.376 ms` |
| External no-exact-anchor p95 latency | `0.5 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.409 ms` |
| External semantic-paraphrase p95 latency | `0.586 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.416 ms` |
| External semantic+no-exact p95 latency | `0.597 ms` |

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
| checkpoint_guard | 5 / 5 | 21.968 | 2.148 |
| code_penalty | 5 / 5 | 27.311 | 2.307 |
| baseline | 5 / 5 | 31.464 | 2.319 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 24.866 | 2.184 |
| 16 | 4 / 5 | 17.704 | 1.283 |
| 64 | 4 / 5 | 28.935 | 3.722 |
| 128 | 4 / 5 | 39.462 | 6.96 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.605` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.368` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.583` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.424` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.36` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.325` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.319` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.219` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.498` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.474` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.354` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.517` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.357` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.393` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.331` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.323` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.205` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.431` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.469` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.457` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.582` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.294` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.33` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.335` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.388` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.236` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.588` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.435` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.505` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.589` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.324` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.339` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.353` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.356` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.241` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.602` |
