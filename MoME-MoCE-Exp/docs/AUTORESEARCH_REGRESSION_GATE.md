# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T19:55:31Z`
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
| Mined policy avg wall | `25.568 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `23.407 ms` |
| Feature avg router | `2.927 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `17.717 ms` |
| Plugin avg router | `3.404 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.503 ms` |
| External p95 latency | `0.808 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.456 ms` |
| External no-exact-anchor p95 latency | `0.614 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.483 ms` |
| External semantic-paraphrase p95 latency | `0.673 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.475 ms` |
| External semantic+no-exact p95 latency | `0.669 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.656 ms` |
| External negative-control mean latency | `0.493 ms` |
| External source-removal pass | `8 / 8` |
| External source-removal avg selected | `0.0` |
| External source-removal p95 latency | `0.539 ms` |
| External source-removal mean latency | `0.384 ms` |

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
| code_penalty | 5 / 5 | 23.407 | 2.927 |
| baseline | 5 / 5 | 29.653 | 3.24 |
| checkpoint_guard | 5 / 5 | 23.348 | 3.355 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 25.568 | 3.187 |
| 16 | 4 / 5 | 18.49 | 1.619 |
| 64 | 4 / 5 | 29.505 | 4.654 |
| 128 | 4 / 5 | 40.477 | 7.744 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.917` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.494` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.644` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.457` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.419` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.413` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.461` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.26` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.465` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.586` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.429` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.633` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.419` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.406` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.427` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.473` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.245` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.483` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.496` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.584` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.699` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.346` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.428` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.442` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.468` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.255` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.633` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.495` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.539` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.662` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.34` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.399` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.433` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.464` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.27` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.673` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.482` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.374` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.637` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.31` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.661` |

## External Source-Removal Sensitivity

| Case | Pass | Removed | Decision | Selected | Latency ms |
|---|---:|---|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `searched_no_authoritative_evidence` | `` | `0.545` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `searched_no_authoritative_evidence` | `` | `0.437` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `searched_no_authoritative_evidence` | `` | `0.527` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `searched_no_authoritative_evidence` | `` | `0.397` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `searched_no_authoritative_evidence` | `` | `0.376` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `searched_no_authoritative_evidence` | `` | `0.352` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `searched_no_authoritative_evidence` | `` | `0.333` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `searched_no_authoritative_evidence` | `` | `0.107` |
