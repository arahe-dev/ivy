# External Generalization Gate

Created: `2026-05-11T18:40:49Z`
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
| Mean latency | `0.406 ms` |
| P50 latency | `0.345 ms` |
| P95 latency | `0.648 ms` |
| Max latency | `0.740 ms` |

## Checks

| Check | Pass |
|---|---:|
| `all_cases_pass` | `True` |
| `required_recall_perfect` | `True` |
| `required_only_precision_perfect` | `True` |
| `no_forbidden_hits` | `True` |
| `mean_latency_under_budget` | `True` |
| `p95_latency_under_budget` | `True` |

## Case Results

| Case | Pass | Decision | Selected | Latency ms |
|---|---:|---|---|---:|
| `cp23_signal_iphone_without_vps` | `True` | `context_packet_ready` | `external_signal_tailscale_webpush` | `0.740` |
| `cp23_signal_not_codex_cloud` | `True` | `context_packet_ready` | `external_signal_not_cloud_service` | `0.343` |
| `cp23_signal_durable_coordination_primitive` | `True` | `context_packet_ready` | `external_signal_event_log` | `0.511` |
| `cp23_signal_daemon_shell_boundary` | `True` | `context_packet_ready` | `external_signal_worker_boundary` | `0.370` |
| `cp23_recall_screenshot_free_context` | `True` | `context_packet_ready` | `external_recall_ai_context` | `0.345` |
| `cp23_recall_text_graph_contents` | `True` | `context_packet_ready` | `external_recall_text_graph` | `0.343` |
| `cp23_recall_graph_ir_role` | `True` | `context_packet_ready` | `external_recall_graph_ir` | `0.337` |
| `cp23_recall_second_brain_features` | `True` | `context_packet_ready` | `external_recall_search_backlinks` | `0.216` |
| `cp23_recall_cloud_price_abstain` | `True` | `searched_no_authoritative_evidence` | `` | `0.453` |
