# Autoresearch Reranker Feature Eval

Winner: `code_penalty` at `max_prefilter_items=32`

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| code_penalty | 5 / 5 | 59.736 | 2.133 |
| checkpoint_guard | 5 / 5 | 61.935 | 2.331 |
| baseline | 5 / 5 | 63.458 | 2.487 |

## Details

### code_penalty

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 2.206 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.459 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.354 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 3.07 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.578 |

### checkpoint_guard

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 2.501 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 2.122 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.698 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 2.93 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.406 |

### baseline

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 3.341 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.802 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.203 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 3.322 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.765 |
