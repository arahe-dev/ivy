# Sample Dry Run Output

```text
dry run complete: autotune_runs\latest
ranked report: autotune_runs\latest\ranked_results.md
```

Expected generated files:

```text
autotune_runs\latest\system_info.json
autotune_runs\latest\model_info.json
autotune_runs\latest\supported_flags.json
autotune_runs\latest\candidates.json
autotune_runs\latest\results.json
autotune_runs\latest\ranked_results.md
autotune_runs\latest\best_config.json
autotune_runs\latest\launch_best.bat
autotune_runs\latest\launch_safe.bat
autotune_runs\latest\override_plans.md
autotune_runs\latest\raw_logs\
```

In dry-run mode, `results.json` is empty and launch scripts report that no successful config is available yet.
