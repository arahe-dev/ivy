# External Generalization Gate

Created: `2026-05-11T20:07:19Z`
Gate passed: `True`
Dataset: `context_stress_external_signal_recall`
Corpus items: `14`
Cases: `9`

## Why This Gate Exists

This gate keeps the MoME/MoCE router honest against non-IVY product and architecture evidence.
It uses the external Signal and Recall Board pack, including decoys and an unsupported commercial-pricing abstention case, so an internal IVY-only benchmark cannot hide overfitting.

## Summary

| Metric | Value |
|---|---:|
| Passed | `9 / 9` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Avg selected | `0.8889` |
| Mean latency | `0.586 ms` |
| P50 latency | `0.501 ms` |
| P95 latency | `1.061 ms` |
| Max latency | `1.226 ms` |

## Checks

| Check | Pass |
|---|---:|
| `all_cases_pass` | `True` |
| `required_recall_perfect` | `True` |
| `required_only_precision_perfect` | `True` |
| `no_forbidden_hits` | `True` |
| `mean_latency_under_budget` | `True` |
| `p95_latency_under_budget` | `True` |
| `no_exact_anchor_all_cases_pass` | `True` |
| `no_exact_anchor_required_recall_perfect` | `True` |
| `no_exact_anchor_required_only_precision_perfect` | `True` |
| `no_exact_anchor_no_forbidden_hits` | `True` |
| `no_exact_anchor_mean_latency_under_budget` | `True` |
| `no_exact_anchor_p95_latency_under_budget` | `True` |
| `semantic_paraphrase_all_cases_pass` | `True` |
| `semantic_paraphrase_required_recall_perfect` | `True` |
| `semantic_paraphrase_required_only_precision_perfect` | `True` |
| `semantic_paraphrase_no_forbidden_hits` | `True` |
| `semantic_paraphrase_mean_latency_under_budget` | `True` |
| `semantic_paraphrase_p95_latency_under_budget` | `True` |
| `semantic_no_exact_anchor_all_cases_pass` | `True` |
| `semantic_no_exact_anchor_required_recall_perfect` | `True` |
| `semantic_no_exact_anchor_required_only_precision_perfect` | `True` |
| `semantic_no_exact_anchor_no_forbidden_hits` | `True` |
| `semantic_no_exact_anchor_mean_latency_under_budget` | `True` |
| `semantic_no_exact_anchor_p95_latency_under_budget` | `True` |
| `negative_control_all_cases_pass` | `True` |
| `negative_control_required_recall_perfect` | `True` |
| `negative_control_required_only_precision_perfect` | `True` |
| `negative_control_no_forbidden_hits` | `True` |
| `negative_control_mean_latency_under_budget` | `True` |
| `negative_control_p95_latency_under_budget` | `True` |
| `source_removal_all_cases_pass` | `True` |
| `source_removal_required_recall_perfect` | `True` |
| `source_removal_required_only_precision_perfect` | `True` |
| `source_removal_no_forbidden_hits` | `True` |
| `source_removal_mean_latency_under_budget` | `True` |
| `source_removal_p95_latency_under_budget` | `True` |
| `semantic_source_removal_all_cases_pass` | `True` |
| `semantic_source_removal_required_recall_perfect` | `True` |
| `semantic_source_removal_required_only_precision_perfect` | `True` |
| `semantic_source_removal_no_forbidden_hits` | `True` |
| `semantic_source_removal_mean_latency_under_budget` | `True` |
| `semantic_source_removal_p95_latency_under_budget` | `True` |

## No Exact Anchor Ablation

This reruns the same external cases with `exact_anchor_memory` disabled. Passing it means the gate is not solely dependent on the exact-anchor expert.

| Metric | Value |
|---|---:|
| Passed | `9 / 9` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Mean latency | `0.469 ms` |
| P95 latency | `0.628 ms` |

## Semantic Paraphrase Ablation

This reruns the external cases with hand-paraphrased queries that avoid copying the original question wording. Passing it means the gate is less dependent on exact query phrasing.

| Metric | Value |
|---|---:|
| Passed | `9 / 9` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Mean latency | `0.485 ms` |
| P95 latency | `0.651 ms` |

## Semantic Paraphrase Without Exact Anchor

This reruns the hand-paraphrased external cases with `exact_anchor_memory` disabled. Passing it means the router can handle the external pack without exact-anchor expert support and without copied query wording.

| Metric | Value |
|---|---:|
| Passed | `9 / 9` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Mean latency | `0.471 ms` |
| P95 latency | `0.624 ms` |

## Negative Control Abstention

This runs near-miss external questions that mention known products but ask for unsupported current facts such as app releases, SLAs, pricing, and certifications. Passing it means the router abstains instead of over-retrieving related identity notes.

| Metric | Value |
|---|---:|
| Passed | `5 / 5` |
| Quality | `1.0000` |
| Required recall | `1.0000` |
| Required-only precision | `1.0000` |
| Forbidden hits | `0` |
| Avg selected | `0.0000` |
| Mean latency | `0.486 ms` |
| P95 latency | `0.684 ms` |

## Source-Removal Sensitivity

This removes each required external source and reruns that case. Passing it means the router abstains instead of selecting adjacent evidence when the necessary source is missing.

| Metric | Value |
|---|---:|
| Passed | `8 / 8` |
| Quality | `1.0000` |
| Required-only precision | `1.0000` |
| Avg selected | `0.0000` |
| Mean latency | `0.377 ms` |
| P95 latency | `0.544 ms` |

## Semantic Source-Removal Sensitivity

This removes each required external source and reruns the hand-paraphrased query. Passing it means required-source causality holds even when the original query wording changes.

| Metric | Value |
|---|---:|
| Passed | `8 / 8` |
| Quality | `1.0000` |
| Required-only precision | `1.0000` |
| Avg selected | `0.0000` |
| Mean latency | `0.373 ms` |
| P95 latency | `0.550 ms` |

## Case Results

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `context_packet_ready` | `external_signal_tailscale_webpush` | `1.226` |
| `cp23_signal_not_codex_cloud` | `True` | `context_packet_ready` | `external_signal_not_cloud_service` | `0.471` |
| `cp23_signal_durable_coordination_primitive` | `True` | `context_packet_ready` | `external_signal_event_log` | `0.813` |
| `cp23_signal_daemon_shell_boundary` | `True` | `context_packet_ready` | `external_signal_worker_boundary` | `0.532` |
| `cp23_recall_screenshot_free_context` | `True` | `context_packet_ready` | `external_recall_ai_context` | `0.576` |
| `cp23_recall_text_graph_contents` | `True` | `context_packet_ready` | `external_recall_text_graph` | `0.501` |
| `cp23_recall_graph_ir_role` | `True` | `context_packet_ready` | `external_recall_graph_ir` | `0.460` |
| `cp23_recall_second_brain_features` | `True` | `context_packet_ready` | `external_recall_search_backlinks` | `0.254` |
| `cp23_recall_cloud_price_abstain` | `True` | `searched_no_authoritative_evidence` | `` | `0.443` |
