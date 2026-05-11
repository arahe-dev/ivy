# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:57:20Z`
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
| Mined policy avg wall | `27.633 ms` |
| Feature profile winner | `checkpoint_guard` |
| Feature pass | `5 / 5` |
| Feature avg wall | `21.212 ms` |
| Feature avg router | `2.05 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `16.544 ms` |
| Plugin avg router | `2.433 ms` |
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
| checkpoint_guard | 5 / 5 | 21.212 | 2.05 |
| baseline | 5 / 5 | 21.436 | 2.146 |
| code_penalty | 5 / 5 | 21.569 | 2.151 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 27.633 | 2.288 |
| 16 | 4 / 5 | 18.295 | 1.379 |
| 64 | 4 / 5 | 30.901 | 4.067 |
| 128 | 4 / 5 | 46.461 | 7.001 |
