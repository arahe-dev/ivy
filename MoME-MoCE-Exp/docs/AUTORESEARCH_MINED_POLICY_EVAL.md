# Autoresearch Mined Case Policy Eval

Created: `2026-05-11T17:33:20Z`

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 46.207 | 2.534 |
| 64 | 5 / 5 | 63.087 | 4.364 |
| 16 | 4 / 5 | 40.153 | 1.135 |
| 128 | 4 / 5 | 77.955 | 6.924 |

## Winner

`max_prefilter_items = 32`

## Rows

### Policy 32

| Case | Pass | Mode | Required | Selected | Router ms |
|---|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | `note_651ce93b6060d428` | 2.347 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.939 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.403 |
| autoresearch_mined_004 | True | abstain_notice | `none` | `none` | 3.238 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | `ing_stash_real_conversation_context_23_ce1a92964a61` | 2.743 |

### Policy 64

| Case | Pass | Mode | Required | Selected | Router ms |
|---|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | `note_651ce93b6060d428` | 5.59 |
| autoresearch_mined_002 | True | proof_lite | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 3.677 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 4.563 |
| autoresearch_mined_004 | True | abstain_notice | `none` | `none` | 4.134 |
| autoresearch_mined_005 | True | proof_lite | `ing_stash_real_conversation_context_23_ce1a92964a61` | `ing_stash_real_conversation_context_23_ce1a92964a61` | 3.858 |

### Policy 16

| Case | Pass | Mode | Required | Selected | Router ms |
|---|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | `note_651ce93b6060d428` | 1.483 |
| autoresearch_mined_002 | False | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | `ing_mome_moce_exp_cp33_plugin_mcp_stdio_2026_0_5_97fa725c5cc9` | 0.89 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 1.201 |
| autoresearch_mined_004 | True | abstain_notice | `none` | `none` | 1.214 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | `note_5806b2ca5c492ccc` | 0.886 |

### Policy 128

| Case | Pass | Mode | Required | Selected | Router ms |
|---|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `ing_mome_moce_exp_cp30_adaptive_packet_and_not_5_0106f9889745` | `note_651ce93b6060d428` | 9.263 |
| autoresearch_mined_002 | False | proof_lite | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | `ing_mome_moce_exp_cp33_plugin_mcp_stdio_2026_0_5_97fa725c5cc9` | 5.232 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 8.64 |
| autoresearch_mined_004 | True | abstain_notice | `none` | `none` | 6.435 |
| autoresearch_mined_005 | True | proof_lite | `ing_stash_real_conversation_context_23_ce1a92964a61` | `ing_stash_real_conversation_context_23_ce1a92964a61` | 5.051 |
