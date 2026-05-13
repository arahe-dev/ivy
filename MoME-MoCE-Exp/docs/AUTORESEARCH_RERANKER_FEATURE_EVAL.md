# Autoresearch Reranker Feature Eval

Winner: `code_penalty` at `max_prefilter_items=32`

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| code_penalty | 5 / 5 | 56.511 | 2.018 |
| baseline | 5 / 5 | 58.432 | 2.167 |
| checkpoint_guard | 5 / 5 | 59.235 | 2.452 |

## Details

### code_penalty

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 2.109 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.489 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.067 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 2.975 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.448 |

### baseline

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 2.573 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.485 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.172 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 3.081 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.523 |

### checkpoint_guard

| Case | Pass | Mode | Selected | Router ms |
|---|---|---|---|---:|
| autoresearch_mined_001 | True | proof_lite | `note_651ce93b6060d428` | 2.949 |
| autoresearch_mined_002 | True | contradiction_aware | `ing_mome_moce_exp_codex_opencode_memory_plugin_2_f2a68a0e6fb4` | 1.732 |
| autoresearch_mined_003 | True | contradiction_aware | `ing_mome_moce_exp_cp42_stale_conflict_plugin_b_1_407aa2f80601, ing_mome_moce_exp_cp42_stale_conflict_plugin_b_2_2bce0c1ce39e` | 2.68 |
| autoresearch_mined_004 | True | abstain_notice | `none` | 3.419 |
| autoresearch_mined_005 | True | contradiction_aware | `ing_stash_real_conversation_context_23_ce1a92964a61` | 1.481 |

## Promotion

- promoted: `True`
- reason: `winner preserves pass rate and improves router latency`
- policy: `C:\ivy\MoME-MoCE-Exp\out\autoresearch_loop\memory_store\policy\autoresearch_policy.json`