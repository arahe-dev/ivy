# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:55:46Z`
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
| Mined policy avg wall | `23.444 ms` |
| Feature profile winner | `baseline` |
| Feature pass | `5 / 5` |
| Feature avg wall | `22.173 ms` |
| Feature avg router | `2.171 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg query wall | `17.054 ms` |
| Plugin avg router | `2.617 ms` |
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
| baseline | 5 / 5 | 22.173 | 2.171 |
| code_penalty | 5 / 5 | 21.981 | 2.476 |
| checkpoint_guard | 5 / 5 | 22.065 | 2.499 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 23.444 | 2.307 |
| 16 | 4 / 5 | 17.885 | 1.173 |
| 64 | 4 / 5 | 29.846 | 4.035 |
| 128 | 4 / 5 | 44.35 | 7.125 |
