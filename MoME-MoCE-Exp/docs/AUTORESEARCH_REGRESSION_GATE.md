# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:46:13Z`
Gate passed: `True`
Mined/feature router budget: `5.0 ms`
Full plugin router budget: `15.0 ms`

## Summary

| Gate | Result |
|---|---:|
| Mined policy winner | `max_prefilter_items=32` |
| Mined policy pass | `5 / 5` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg router | `2.149 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg router | `2.411 ms` |
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
| checkpoint_guard | 5 / 5 | 29.995 | 2.149 |
| baseline | 5 / 5 | 36.087 | 2.215 |
| code_penalty | 5 / 5 | 29.867 | 2.257 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 31.741 | 2.212 |
| 16 | 4 / 5 | 25.342 | 1.212 |
| 64 | 4 / 5 | 42.449 | 3.916 |
| 128 | 4 / 5 | 60.73 | 6.735 |
