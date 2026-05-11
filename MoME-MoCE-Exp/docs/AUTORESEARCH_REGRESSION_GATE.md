# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:43:47Z`
Gate passed: `True`
Mined/feature router budget: `5.0 ms`
Full plugin router budget: `15.0 ms`

## Summary

| Gate | Result |
|---|---:|
| Mined policy winner | `max_prefilter_items=32` |
| Mined policy pass | `5 / 5` |
| Feature profile winner | `baseline` |
| Feature pass | `5 / 5` |
| Feature avg router | `2.137 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg router | `2.515 ms` |
| Promotion | `False` |

## Checks

| Check | Pass |
|---|---:|
| `mined_policy_all_pass` | `True` |
| `feature_eval_all_pass` | `True` |
| `plugin_benchmark_all_pass` | `True` |
| `feature_router_under_budget` | `True` |
| `plugin_router_under_budget` | `True` |

## Feature Profiles

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| baseline | 5 / 5 | 59.076 | 2.137 |
| checkpoint_guard | 5 / 5 | 56.462 | 2.184 |
| code_penalty | 5 / 5 | 56.926 | 2.268 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 56.848 | 2.26 |
| 16 | 4 / 5 | 51.912 | 1.24 |
| 64 | 4 / 5 | 67.168 | 3.703 |
| 128 | 4 / 5 | 95.614 | 7.643 |
