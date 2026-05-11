# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:51:42Z`
Gate passed: `True`
Mined/feature router budget: `5.0 ms`
Full plugin router budget: `15.0 ms`
Mined/feature wall budget: `50.0 ms`
Full plugin wall budget: `40.0 ms`

## Summary

| Gate | Result |
|---|---:|
| Mined policy winner | `max_prefilter_items=32` |
| Mined policy pass | `5 / 5` |
| Mined policy avg wall | `30.718 ms` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg wall | `29.088 ms` |
| Feature avg router | `2.153 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `29.071 ms` |
| Plugin avg router | `2.732 ms` |
| Promotion | `False` |

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

## Feature Profiles

| Profile | Passed | Avg wall ms | Avg router ms |
|---|---:|---:|---:|
| code_penalty | 5 / 5 | 29.088 | 2.153 |
| checkpoint_guard | 5 / 5 | 29.629 | 2.213 |
| baseline | 5 / 5 | 35.744 | 2.789 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 30.718 | 2.329 |
| 16 | 4 / 5 | 24.9 | 1.208 |
| 64 | 4 / 5 | 36.412 | 3.97 |
| 128 | 4 / 5 | 46.391 | 7.361 |
