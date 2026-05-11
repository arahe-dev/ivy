# Autoresearch Context Memory Regression Gate

Created: `2026-05-11T17:42:06Z`
Gate passed: `True`
Mined/feature router budget: `5.0 ms`
Full plugin router budget: `15.0 ms`

## Summary

| Gate | Result |
|---|---:|
| Mined policy winner | `max_prefilter_items=32` |
| Mined policy pass | `5 / 5` |
| Feature profile winner | `code_penalty` |
| Feature pass | `5 / 5` |
| Feature avg router | `2.043 ms` |
| Plugin benchmark pass | `6 / 6` |
| Plugin avg router | `11.327 ms` |
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
| code_penalty | 5 / 5 | 56.535 | 2.043 |
| checkpoint_guard | 5 / 5 | 54.153 | 2.134 |
| baseline | 5 / 5 | 55.846 | 2.135 |

## Mined Policy Candidates

| max_prefilter_items | Passed | Avg wall ms | Avg router ms |
|---:|---:|---:|---:|
| 32 | 5 / 5 | 55.756 | 2.096 |
| 16 | 4 / 5 | 52.149 | 1.145 |
| 64 | 4 / 5 | 70.18 | 3.748 |
| 128 | 4 / 5 | 95.454 | 7.188 |
