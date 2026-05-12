# Autoresearch Context Memory Regression Gate

Created: `2026-05-12T03:06:30Z`
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
| Mined policy avg wall | `26.243 ms` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg wall | `27.339 ms` |
| Feature avg router | `2.5 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `19.061 ms` |
| Plugin avg router | `3.546 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.514 ms` |
| External p95 latency | `0.721 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.506 ms` |
| External no-exact-anchor p95 latency | `0.699 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.639 ms` |
| External semantic-paraphrase p95 latency | `0.906 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.531 ms` |
| External semantic+no-exact p95 latency | `0.699 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.717 ms` |
| External negative-control mean latency | `0.528 ms` |
| External source-removal pass | `8 / 8` |
| External source-removal avg selected | `0.0` |
| External source-removal p95 latency | `0.601 ms` |
| External source-removal mean latency | `0.409 ms` |
| External semantic source-removal pass | `8 / 8` |
| External semantic source-removal avg selected | `0.0` |
| External semantic source-removal p95 latency | `0.584 ms` |
| External semantic source-removal mean latency | `0.388 ms` |

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
| checkpoint_guard | 5 / 5 | 27.339 | 2.5 |
| code_penalty | 5 / 5 | 26.498 | 2.573 |
| baseline | 5 / 5 | 34.033 | 2.615 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 26.243 | 2.584 |
| 16 | 4 / 5 | 26.259 | 1.669 |
| 64 | 4 / 5 | 31.256 | 4.512 |
| 128 | 4 / 5 | 49.929 | 8.595 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.729` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.489` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.708` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.473` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.468` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.44` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.508` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.263` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.544` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.703` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.491` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.693` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.475` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.466` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.443` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.506` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.278` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.496` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.63` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.593` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `1.046` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.681` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.448` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.636` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.697` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.342` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.68` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.548` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.617` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.741` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.431` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.52` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.514` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.503` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.27` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.635` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.477` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.416` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.665` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.352` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.73` |

## External Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.607` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.47` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.591` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.416` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.397` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.338` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.337` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.117` |

## External Semantic Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.32` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.544` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.605` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.348` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.398` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.368` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.383` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.136` |
