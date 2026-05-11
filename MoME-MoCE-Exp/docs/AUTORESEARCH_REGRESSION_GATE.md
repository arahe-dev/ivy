# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T20:07:37Z`
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
| Mined policy avg wall | `26.275 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `24.665 ms` |
| Feature avg router | `3.144 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `19.1 ms` |
| Plugin avg router | `4.115 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.492 ms` |
| External p95 latency | `0.757 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.471 ms` |
| External no-exact-anchor p95 latency | `0.607 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.482 ms` |
| External semantic-paraphrase p95 latency | `0.649 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.561 ms` |
| External semantic+no-exact p95 latency | `0.824 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.86 ms` |
| External negative-control mean latency | `0.59 ms` |
| External source-removal pass | `8 / 8` |
| External source-removal avg selected | `0.0` |
| External source-removal p95 latency | `0.576 ms` |
| External source-removal mean latency | `0.402 ms` |
| External semantic source-removal pass | `8 / 8` |
| External semantic source-removal avg selected | `0.0` |
| External semantic source-removal p95 latency | `0.623 ms` |
| External semantic source-removal mean latency | `0.416 ms` |

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
| code_penalty | 5 / 5 | 24.665 | 3.144 |
| checkpoint_guard | 5 / 5 | 26.54 | 3.618 |
| baseline | 5 / 5 | 35.796 | 4.067 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 26.275 | 3.065 |
| 16 | 4 / 5 | 21.17 | 1.654 |
| 64 | 4 / 5 | 29.465 | 4.901 |
| 128 | 4 / 5 | 42.905 | 8.235 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.828` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.46` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.651` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.446` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.412` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.414` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.527` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.259` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.434` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.588` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.462` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.62` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.437` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.416` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.453` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.555` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.254` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.456` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.508` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.559` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.659` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.366` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.402` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.458` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.48` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.271` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.634` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.556` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.568` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.727` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.392` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.439` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.46` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.889` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.305` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.716` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.511` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.489` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.673` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.37` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.907` |

## External Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.584` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.452` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.561` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.401` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.403` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.34` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.348` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.13` |

## External Semantic Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.322` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.646` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.579` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.325` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.406` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.521` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.39` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.138` |
