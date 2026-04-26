# Progress Guard Spec

## Purpose

Prevent the agent loop from wasting turns or failing after all required observations are already available.

## Detection Rules

1. Same tool and same arguments already executed.
2. `fs_read` targets a path already present in `already_read_paths`.
3. Required `fixtures/...` source files inferred from the task/success requirements are all read, but the model proposes another `fs_read`.
4. Proposed tool call matches the previous progress key and would not add new state.

## Behavior

- Do not execute the stalled tool call.
- Append a `progress_guard` event to dynamic history.
- Write `progress_guard_<step>.json`.
- Add a `progress_guard_blocked` step in `run_summary.json`.
- Continue the normal loop.
- Do not consume or increase the validator repair budget unless the model output itself is invalid JSON/schema.

## Metadata

Each `run_summary.json` includes:

- `repeated_tool_blocked_count`
- `progress_guard_triggered_count`
- `already_read_paths`
- `observed_tool_results_count`
- `last_distinct_tool_call`
- `progress_notes`
