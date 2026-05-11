# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T19:37:58Z`
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
| Mined policy avg wall | `25.298 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `21.191 ms` |
| Feature avg router | `2.068 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `16.598 ms` |
| Plugin avg router | `2.454 ms` |
| Promotion | `False` |
| External generalization pass | `9 / 9` |
| External required precision | `1.0` |
| External forbidden hits | `0` |
| External mean latency | `0.378 ms` |
| External p95 latency | `0.522 ms` |
| External no-exact-anchor pass | `9 / 9` |
| External no-exact-anchor mean latency | `0.385 ms` |
| External no-exact-anchor p95 latency | `0.516 ms` |
| External semantic-paraphrase pass | `9 / 9` |
| External semantic-paraphrase mean latency | `0.415 ms` |
| External semantic-paraphrase p95 latency | `0.601 ms` |
| External semantic+no-exact pass | `9 / 9` |
| External semantic+no-exact mean latency | `0.412 ms` |
| External semantic+no-exact p95 latency | `0.631 ms` |
| External negative-control pass | `5 / 5` |
| External negative-control avg selected | `0.0` |
| External negative-control p95 latency | `0.674 ms` |
| External negative-control mean latency | `0.504 ms` |

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
| code_penalty | 5 / 5 | 21.191 | 2.068 |
| checkpoint_guard | 5 / 5 | 21.349 | 2.115 |
| baseline | 5 / 5 | 29.707 | 2.128 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 25.298 | 2.217 |
| 16 | 4 / 5 | 17.962 | 1.161 |
| 64 | 4 / 5 | 28.949 | 3.899 |
| 128 | 4 / 5 | 38.979 | 6.796 |

## External Generalization

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.528` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.339` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.513` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.364` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.362` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.308` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.329` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.213` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.447` |

## External No-Exact-Anchor Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `external_signal_tailscale_webpush` | `0.444` |
| `cp23_signal_not_codex_cloud` | `True` | `external_signal_not_cloud_service` | `0.338` |
| `cp23_signal_durable_coordination_primitive` | `True` | `external_signal_event_log` | `0.529` |
| `cp23_signal_daemon_shell_boundary` | `True` | `external_signal_worker_boundary` | `0.344` |
| `cp23_recall_screenshot_free_context` | `True` | `external_recall_ai_context` | `0.405` |
| `cp23_recall_text_graph_contents` | `True` | `external_recall_text_graph` | `0.339` |
| `cp23_recall_graph_ir_role` | `True` | `external_recall_graph_ir` | `0.348` |
| `cp23_recall_second_brain_features` | `True` | `external_recall_search_backlinks` | `0.218` |
| `cp23_recall_cloud_price_abstain` | `True` | `` | `0.497` |

## External Semantic Paraphrase Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.45` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.448` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.555` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.313` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.344` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.353` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.391` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.25` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.632` |

## External Semantic Plus No-Exact Ablation

| Case | Pass | Selected | Latency ms |
|---|---:|---|---:|
| `cp23_signal_iphone_without_vps_semantic_paraphrase` | `True` | `external_signal_tailscale_webpush` | `0.371` |
| `cp23_signal_not_codex_cloud_semantic_paraphrase` | `True` | `external_signal_not_cloud_service` | `0.448` |
| `cp23_signal_durable_coordination_primitive_semantic_paraphrase` | `True` | `external_signal_event_log` | `0.551` |
| `cp23_signal_daemon_shell_boundary_semantic_paraphrase` | `True` | `external_signal_worker_boundary` | `0.312` |
| `cp23_recall_screenshot_free_context_semantic_paraphrase` | `True` | `external_recall_ai_context` | `0.334` |
| `cp23_recall_text_graph_contents_semantic_paraphrase` | `True` | `external_recall_text_graph` | `0.371` |
| `cp23_recall_graph_ir_role_semantic_paraphrase` | `True` | `external_recall_graph_ir` | `0.386` |
| `cp23_recall_second_brain_features_semantic_paraphrase` | `True` | `external_recall_search_backlinks` | `0.249` |
| `cp23_recall_cloud_price_abstain_semantic_paraphrase` | `True` | `` | `0.685` |

## External Negative Controls

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `neg_signal_android_play_store_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.466` |
| `neg_signal_hosted_sla` | `True` | `searched_no_authoritative_evidence` | `` | `0.393` |
| `neg_recall_cloud_price` | `True` | `searched_no_authoritative_evidence` | `` | `0.648` |
| `neg_recall_mobile_app_release` | `True` | `searched_no_authoritative_evidence` | `` | `0.333` |
| `neg_recall_soc2` | `True` | `searched_no_authoritative_evidence` | `` | `0.68` |
