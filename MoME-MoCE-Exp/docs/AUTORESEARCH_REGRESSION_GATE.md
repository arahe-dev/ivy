# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:47:52Z`
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
| Feature avg router | `2.074 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg router | `2.564 ms` |
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
| checkpoint_guard | 5 / 5 | 28.1 | 2.074 |
| code_penalty | 5 / 5 | 28.732 | 2.117 |
| baseline | 5 / 5 | 36.597 | 2.345 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 31.69 | 2.252 |
| 16 | 4 / 5 | 24.714 | 1.221 |
| 64 | 4 / 5 | 36.766 | 3.801 |
| 128 | 4 / 5 | 46.542 | 6.923 |
