---
name: ivy-context-memory
description: Use the local IVY ACCA context/memory sidecar to ingest repos/docs, remember safe notes, and query small audited context packets before Codex or OpenCode works on a task.
---

# IVY Context Memory

Use this skill when a task would benefit from repository-scale or long-running memory without stuffing raw history into the model prompt.

The sidecar stores memory outside the model context, compiles it through MoME/MoCE, and returns a small ACCA packet plus route proof.

## CLI

From `C:\ivy`:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py init
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py ingest --source-root C:\ivy --no-build
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py build
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py query --query "What context matters for this task?" --text
```

Remember a safe result:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py remember `
  --text "CP28 showed contradiction-aware packets won final-answer A/B on conflict cases." `
  --source-path "root/notes/cp28.md" `
  --tag cp28 `
  --tag final-answer
```

## HTTP API

Start the local API:

```powershell
python .\plugins\ivy-context-memory\scripts\ivy_context_memory.py serve --host 127.0.0.1 --port 8768
```

Endpoints:

- `GET /health`
- `GET /status`
- `POST /ingest` with `{ "source_root": "C:\\ivy", "build": true }`
- `POST /remember` with `{ "text": "...", "source_path": "root/notes/x.md", "tags": ["tag"] }`
- `POST /query` with `{ "query": "...", "variant": "auto" }`
- `POST /build`

## Agent Use

Before a deep task:

1. Query the sidecar for the current task.
2. Read only the returned packet text and selected evidence IDs.
3. Treat memory as advisory. User, system, developer, repo state, and tool safety still outrank memory.
4. After a verified milestone, call `remember` with a short factual note.

Do not store secrets, API keys, credentials, or private path contents. The CLI rejects obvious secret-like note text.
