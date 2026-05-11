# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T20:21:53Z`
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
| Mined policy avg wall | `25.594 ms` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg wall | `22.543 ms` |
| Feature avg router | `2.888 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `18.043 ms` |
| Plugin avg router | `4.128 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.539 ms` |
| External p95 latency | `0.754 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.542 ms` |
| External no-exact-anchor p95 latency | `0.954 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.504 ms` |
| External semantic-paraphrase p95 latency | `0.687 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.632 ms` |
| External semantic+no-exact p95 latency | `0.794 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.804 ms` |
| External negative-control mean latency | `0.591 ms` |
| External source-removal pass | `8 / 8` |
| External source-removal avg selected | `0.0` |
| External source-removal p95 latency | `0.852 ms` |
| External source-removal mean latency | `0.508 ms` |
| External semantic source-removal pass | `8 / 8` |
| External semantic source-removal avg selected | `0.0` |
| External semantic source-removal p95 latency | `0.662 ms` |
| External semantic source-removal mean latency | `0.466 ms` |

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
| checkpoint_guard | 5 / 5 | 22.543 | 2.888 |
| code_penalty | 5 / 5 | 22.082 | 2.979 |
| baseline | 5 / 5 | 30.466 | 3.061 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 25.594 | 3.158 |
| 16 | 4 / 5 | 18.145 | 1.595 |
| 64 | 4 / 5 | 29.314 | 4.654 |
| 128 | 4 / 5 | 40.56 | 7.625 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.775` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.66` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.723` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.47` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.48` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.449` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.526` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.277` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.495` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `1.126` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.492` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.697` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.47` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.456` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.431` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.503` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.246` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.46` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.5` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.592` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.711` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.385` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.441` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.491` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.49` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.278` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.652` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.651` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.623` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.713` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.408` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.441` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.545` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.825` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.748` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.736` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.55` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.443` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.776` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.375` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.811` |

## External Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.62` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.535` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.664` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.428` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.953` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.396` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.345` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.122` |

## External Semantic Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.332` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.578` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.708` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.546` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.491` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.447` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.469` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.153` |
