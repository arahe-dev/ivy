# Autoresearch Mined Failures And Hard Cases

Created: `2026-05-11T17:31:49Z`

Mined cases: `5`

| Query | Reason | Severity | Fastest policy | Deepest policy | Latency spread ms |
|---|---|---|---|---|---:|
| What did CP28 show about final answer packet formats? | latency_sensitive_to_prefilter_depth | medium | `32` -> `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | `192` -> `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | 10.078 |
| What MCP tools does ivy-context-memory expose? | selection_changes_with_prefilter_depth | medium | `32` -> `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | `192` -> `ing_mome_moce_exp_cp33_plugin_mcp_stdio_2026_0_5_97fa725c5cc9` | 5.66 |
| What is the latest CP42 rebuild policy versus stale memory? | latency_sensitive_to_prefilter_depth | medium | `32` -> `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | `192` -> `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 11.147 |
| What is today's Bitcoin price? | latency_sensitive_to_prefilter_depth | medium | `32` -> `none` | `192` -> `none` | 5.621 |
| What do real conversations ask us to build for IVY memory? | latency_sensitive_to_prefilter_depth | medium | `32` -> `ing_stash_real_conversation_context_23_ce1a92964a61` | `192` -> `ing_stash_real_conversation_context_23_ce1a92964a61` | 6.835 |

## Use

These are not all failures. They are failure-like or hard cases mined from policy sensitivity, selection drift, packet-mode drift, or outright expectation misses.
Future reranker and router changes should preserve or improve these cases.
