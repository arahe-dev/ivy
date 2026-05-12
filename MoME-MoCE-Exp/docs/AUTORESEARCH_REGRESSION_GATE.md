# Autoresearch Context Memory Regression Gate

Created: `2026-05-12T03:25:36Z`
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
| Mined policy avg wall | `27.577 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `23.652 ms` |
| Feature avg router | `2.431 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `19.351 ms` |
| Plugin avg router | `3.747 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.579 ms` |
| External p95 latency | `0.949 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.532 ms` |
| External no-exact-anchor p95 latency | `0.825 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.587 ms` |
| External semantic-paraphrase p95 latency | `1.18 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.535 ms` |
| External semantic+no-exact p95 latency | `0.704 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.694 ms` |
| External negative-control mean latency | `0.512 ms` |
| External source-removal pass | `8 / 8` |
| External source-removal avg selected | `0.0` |
| External source-removal p95 latency | `0.59 ms` |
| External source-removal mean latency | `0.404 ms` |
| External semantic source-removal pass | `8 / 8` |
| External semantic source-removal avg selected | `0.0` |
| External semantic source-removal p95 latency | `0.622 ms` |
| External semantic source-removal mean latency | `0.43 ms` |

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
| `external_all_cases_pass` | `True` |
| `external_required_recall_perfect` | `True` |
| `external_required_only_precision_perfect` | `True` |
| `external_no_forbidden_hits` | `True` |
| `external_mean_latency_under_budget` | `True` |
| `external_p95_latency_under_budget` | `True` |
| `external_no_exact_anchor_all_cases_pass` | `True` |
| `external_no_exact_anchor_required_recall_perfect` | `True` |
| `external_no_exact_anchor_required_only_precision_perfect` | `True` |
| `external_no_exact_anchor_no_forbidden_hits` | `True` |
| `external_no_exact_anchor_mean_latency_under_budget` | `True` |
| `external_no_exact_anchor_p95_latency_under_budget` | `True` |
| `external_semantic_paraphrase_all_cases_pass` | `True` |
| `external_semantic_paraphrase_required_recall_perfect` | `True` |
| `external_semantic_paraphrase_required_only_precision_perfect` | `True` |
| `external_semantic_paraphrase_no_forbidden_hits` | `True` |
| `external_semantic_paraphrase_mean_latency_under_budget` | `True` |
| `external_semantic_paraphrase_p95_latency_under_budget` | `True` |
| `external_semantic_no_exact_anchor_all_cases_pass` | `True` |
| `external_semantic_no_exact_anchor_required_recall_perfect` | `True` |
| `external_semantic_no_exact_anchor_required_only_precision_perfect` | `True` |
| `external_semantic_no_exact_anchor_no_forbidden_hits` | `True` |
| `external_semantic_no_exact_anchor_mean_latency_under_budget` | `True` |
| `external_semantic_no_exact_anchor_p95_latency_under_budget` | `True` |
| `external_negative_control_all_cases_pass` | `True` |
| `external_negative_control_required_recall_perfect` | `True` |
| `external_negative_control_required_only_precision_perfect` | `True` |
| `external_negative_control_no_forbidden_hits` | `True` |
| `external_negative_control_mean_latency_under_budget` | `True` |
| `external_negative_control_p95_latency_under_budget` | `True` |
| `external_source_removal_all_cases_pass` | `True` |
| `external_source_removal_required_recall_perfect` | `True` |
| `external_source_removal_required_only_precision_perfect` | `True` |
| `external_source_removal_no_forbidden_hits` | `True` |
| `external_source_removal_mean_latency_under_budget` | `True` |
| `external_source_removal_p95_latency_under_budget` | `True` |
| `external_semantic_source_removal_all_cases_pass` | `True` |
| `external_semantic_source_removal_required_recall_perfect` | `True` |
| `external_semantic_source_removal_required_only_precision_perfect` | `True` |
| `external_semantic_source_removal_no_forbidden_hits` | `True` |
| `external_semantic_source_removal_mean_latency_under_budget` | `True` |
| `external_semantic_source_removal_p95_latency_under_budget` | `True` |

## Feature Profiles

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| code_penalty | 5 / 5 | 23.652 | 2.431 |
| checkpoint_guard | 5 / 5 | 23.073 | 2.582 |
| baseline | 5 / 5 | 34.626 | 2.599 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 27.577 | 2.571 |
| 16 | 4 / 5 | 19.439 | 1.634 |
| 64 | 4 / 5 | 31.782 | 4.624 |
| 128 | 4 / 5 | 44.667 | 7.865 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `1.045` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.525` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.71` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.481` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.463` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.449` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.806` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.27` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.462` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.867` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.518` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.761` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.49` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.461` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.432` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.517` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.269` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.472` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.475` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.575` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.71` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.375` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.432` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.47` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.49` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.266` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `1.493` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.617` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.66` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.733` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.451` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.456` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.481` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.496` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.276` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.643` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.456` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.407` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.64` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.35` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.708` |

## External Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.606` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.459` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.56` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.405` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.411` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.34` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.334` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.117` |

## External Semantic Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.34` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.58` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.645` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.357` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.456` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.442` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.457` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.166` |
