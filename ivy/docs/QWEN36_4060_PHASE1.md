# Qwen 3.6 35B-A3B RTX 4060 Phase 1

Phase 1 is a measurement-only benchmark harness for llama.cpp on a Windows RTX 4060 8GB laptop. It does not optimize, autotune, select runtime profiles, change agent behavior, add kernels, or modify planner/memory systems.

## Run

Edit `ivy/manifests/qwen36_4060_baseline.yaml` with local paths, or pass overrides:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\bench_qwen36_4060.ps1 `
  -ModelPath C:\path\to\qwen.gguf `
  -LlamaServerPath C:\path\to\llama-server.exe `
  -StopServerAfter
```

Outputs are written under:

```text
runs/qwen36_4060_bench/<timestamp>/
```

Each matrix item gets its own folder with `config.json`, `request.json`, `response.json` when available, server logs, command text, and result or failure metadata.

## Smoke Test

Use `-DryRun` to validate matrix expansion without launching a model:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\bench_qwen36_4060.ps1 -DryRun -MaxRuns 3
```

For a tiny real run:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\bench_qwen36_4060.ps1 `
  -MaxRuns 1 `
  -ModelPath C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf `
  -LlamaServerPath C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe `
  -StopServerAfter
```

## Matrix

The default matrix covers context sizes `512`, `1024`, and `2048`; KV cache types `f16`, `q8_0`, and `q4_0` for both K and V; CPU MoE on/off; conservative GPU layer counts; and three prompt shapes: short completion, JSON-only tool call, and a longer static-prefix-style prompt.

Use `-MaxRuns` or `-MatrixLimit` to reduce the matrix for smoke tests.

## Metrics

`ivy/scripts/collect_qwen36_metrics.py` parses benchmark artifacts and writes:

- `summary.csv`
- `summary.json`
- `report.md`

`summary.csv` includes config name, model identifier, ctx, cache types, CPU MoE flag, GPU layers, prompt name, HTTP success/failure, startup/load failure, llama.cpp timing fields when present, approximate decode TPS, wall time, first-token field when exposed, JSON validity for the JSON prompt, and error messages.

Blank or null fields mean llama.cpp did not expose that metric reliably in the captured response. The collector does not invent timing values.

## Limitations

- The manifest uses placeholder paths by default.
- CPU MoE support depends on the local llama.cpp build and model.
- First-token latency is only recorded if the server response exposes a compatible field.
- The harness starts one server per config to keep measurements isolated.
- Phase 1 does not decide which configuration is best; it only records reproducible measurements.
- Early tiny smoke runs for similar configs observed different decode rates, including about `12.68 tok/s` and an ingested run around `19.616 decode_tps`. Treat single-run TPS as preliminary and unstable.
- Ingest benchmark outputs with `python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\qwen36_4060_bench` before evaluating Qwen benchmark memory retrieval.
