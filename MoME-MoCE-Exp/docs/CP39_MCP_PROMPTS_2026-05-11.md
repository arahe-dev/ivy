# CP39 MCP Prompts - 2026-05-11

## What Changed

The `ivy-context-memory` MCP server now exposes prompts:

- `query_ivy_memory_before_task`
- `remember_verified_milestone`

Implemented MCP methods:

- `prompts/list`
- `prompts/get`

## Prompt Behavior

### `query_ivy_memory_before_task`

Argument:

- `task`

Returns a user message telling the agent to call `ivy_memory_query`, treat the packet as advisory context, and then work on the supplied task.

### `remember_verified_milestone`

Argument:

- `milestone`

Returns a user message telling the agent to call `ivy_memory_remember` only after verification, without storing secrets or unverified claims.

## Verification

The plugin MCP test now launches the server and verifies:

- `prompts/list` includes `query_ivy_memory_before_task`
- `prompts/get` returns a text message containing `ivy_memory_query`
- prompt arguments are interpolated into the returned prompt text

## Why This Matters

Tools and resources make the plugin callable. Prompts make it teachable.

An MCP-aware client can now expose these as reusable workflows:

```mermaid
flowchart LR
  User["User task"] --> Prompt["query_ivy_memory_before_task"]
  Prompt --> Agent["Agent calls ivy_memory_query"]
  Agent --> Work["Implementation / verification"]
  Work --> RememberPrompt["remember_verified_milestone"]
  RememberPrompt --> Memory["ivy_memory_remember"]
```

This is a practical step toward making MoME/MoCE memory a normal part of Codex/OpenCode operation instead of a manual side command.
