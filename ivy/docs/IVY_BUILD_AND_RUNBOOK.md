# IVY Build And Runbook

Assumptions:

- Repo root is `C:\ivy`.
- Commands are Windows-first.
- Python is available as `python`.
- Qwen local paths are optional and only needed for Qwen smoke runs.

## Memory DB

```powershell
cd C:\ivy
python -m ivy_agent_demo.memory_cli init
```

Ingest agent runs:

```powershell
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\phase1_agent_demo
```

Ingest Qwen benchmark runs:

```powershell
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\qwen36_4060_bench
```

Stats:

```powershell
python -m ivy_agent_demo.memory_cli stats
```

Search:

```powershell
python -m ivy_agent_demo.memory_cli search --query "json validation failed"
python -m ivy_agent_demo.memory_cli vector-search --query "model emitted think tags before JSON"
python -m ivy_agent_demo.memory_cli hybrid-search --query "qwen ctx 512 decode_tps"
```

## Memory Eval

Real DB eval:

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest
```

Synthetic eval:

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --build-synthetic-db --top-k 5 --compare-latest
```

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_eval.ps1 -BuildSyntheticDb -CompareLatest
```

Helper with ingestion:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_eval.ps1 `
  -IngestBeforeEval `
  -RunsRoot C:\ivy\runs\phase1_agent_demo `
  -CompareLatest
```

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_eval.ps1 `
  -IngestBeforeEval `
  -RunsRoot C:\ivy\runs\qwen36_4060_bench `
  -TopK 5 `
  -CompareLatest
```

Memory eval outputs:

```text
C:\ivy\runs\memory_eval\<timestamp>\
  memory_eval_config.json
  memory_eval_report.md
  memory_eval_results.csv
  memory_eval_results.json
```

History:

```text
C:\ivy\runs\memory_eval\history.jsonl
C:\ivy\runs\memory_eval\history.csv
```

## Memory Packet Preview

```powershell
python -m ivy_agent_demo.memory_packet_cli preview --query "json tool call failed because qwen emitted think tags" --policy failure_first --top-k 5
python -m ivy_agent_demo.memory_packet_cli preview --query "benchmark qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 5
python -m ivy_agent_demo.memory_packet_cli compare --query "json tool call failed because qwen emitted think tags" --policies keyword_only vector_only hybrid_default failure_first
python -m ivy_agent_demo.memory_packet_eval --cases ivy_agent_demo/memory_packet_eval_cases.json --compare-latest
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\preview_memory_packet.ps1 `
  -Query "json tool call failed because qwen emitted think tags" `
  -Policy failure_first `
  -TopK 5
```

Packet artifacts are written under `C:\ivy\runs\memory_packet_preview\<timestamp>\`.

## Qwen Benchmark Smoke

Only run this if both local paths exist:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\bench_qwen36_4060.ps1 `
  -MaxRuns 1 `
  -ModelPath C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf `
  -LlamaServerPath C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe `
  -StopServerAfter
```

Qwen benchmark outputs:

```text
C:\ivy\runs\qwen36_4060_bench\<timestamp>\
```

Each config folder contains `config.json`, `request.json`, `response.json` when available, logs, `server_command.txt`, and `result.json` or `failure.json`.

## Compile Check

```powershell
python -m py_compile ivy_agent_demo\memory_store.py ivy_agent_demo\memory_ingest.py ivy_agent_demo\memory_search.py ivy_agent_demo\memory_cli.py ivy_agent_demo\memory_eval.py
```
