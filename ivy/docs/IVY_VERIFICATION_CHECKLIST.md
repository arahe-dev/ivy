# IVY Verification Checklist

Run from repo root:

```powershell
cd C:\ivy
```

## A. Memory DB exists and has rows

```powershell
python -m ivy_agent_demo.memory_cli stats
```

Expected after ingestion: nonzero `episodes`, `memory_items`, and `memory_vectors`.

## B. FTS available

```powershell
python -m ivy_agent_demo.memory_cli stats
```

Expected on current machine:

```text
fts5_available: True
```

## C. Vector fallback working

```powershell
python -m ivy_agent_demo.memory_cli vector-search --query "model emitted think tags before JSON"
```

Expected: results with `score` and provenance when matching memories exist.

## D. Hybrid search returns provenance

```powershell
python -m ivy_agent_demo.memory_cli hybrid-search --query "qwen ctx 512 decode_tps"
```

Expected: result rows include `artifact=...` or run provenance when Qwen benchmark memories exist.

## E. Synthetic eval passes

```powershell
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --build-synthetic-db --top-k 5 --compare-latest
```

Expected: top-1/top-3/top-k/provenance rates are `1.0`.

## F. Real eval after ingestion has nonzero hit rate

```powershell
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\phase1_agent_demo
python -m ivy_agent_demo.memory_cli ingest --runs-root C:\ivy\runs\qwen36_4060_bench
python -m ivy_agent_demo.memory_eval --cases ivy_agent_demo/memory_eval_cases.json --top-k 5 --compare-latest
```

Expected: nonzero hit rate. Current known post-ingestion checkpoint was `0.75`.

## G. Qwen smoke can run if local paths exist

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\bench_qwen36_4060.ps1 `
  -MaxRuns 1 `
  -ModelPath C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf `
  -LlamaServerPath C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe `
  -StopServerAfter
```

Expected: one timestamped run under `C:\ivy\runs\qwen36_4060_bench`.

## H. Agent runtime unchanged

```powershell
git diff -- ivy_agent_demo\agent_loop.py ivy_agent_demo\validator.py ivy_agent_demo\policy.py ivy_agent_demo\tools.py
```

Expected for this memory consolidation pass: no diff.

## I. Packet preview is passive

```powershell
python -m ivy_agent_demo.memory_packet_cli self-test
python -m ivy_agent_demo.memory_packet_cli preview --query "benchmark qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 5
python -m ivy_agent_demo.memory_packet_eval --cases ivy_agent_demo/memory_packet_eval_cases.json --compare-latest
```

Expected: packet artifacts are saved under `C:\ivy\runs\memory_packet_preview`; no prompt injection or agent runtime diff.

Expected after Phase 2B: duplicate-heavy packets report `duplicate_group_count > 0`, `compression_ratio < 1`, and grouped evidence in `packet_report.md`.

## J. Broader packet sweep runs

```powershell
python -m ivy_agent_demo.memory_packet_sweep --self-test
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --compare-latest --inspect-failures
python -m ivy_agent_demo.memory_packet_sweep --cases ivy_agent_demo/memory_packet_eval_real_cases.json --category safety --compare-latest --inspect-failures
```

Expected: sweep reports under `C:\ivy\runs\memory_packet_sweep`; no prompt injection or agent runtime diff.

## K. Memory coverage backfill

```powershell
python -m ivy_agent_demo.memory_doc_ingest --all-defaults --dry-run
python -m ivy_agent_demo.memory_doc_ingest --all-defaults --include-source
python -m ivy_agent_demo.memory_coverage_check
python -m ivy_agent_demo.memory_coverage_check --category safety
```

Expected: coverage reports under `C:\ivy\runs\memory_coverage`; safety/docs/workflow memories have source artifact paths.

Helper:

```powershell
powershell -ExecutionPolicy Bypass -File ivy\scripts\rerun_memory_coverage.ps1 -AllDefaults -IncludeSource -RunSweepAfter -CompareLatest
```

## L. Ranking cleanup

```powershell
python -m ivy_agent_demo.memory_ranking_eval --self-test
python -m ivy_agent_demo.memory_packet_cli diagnose-ranking --query "qwen 4060 ctx 512 decode_tps" --policy benchmark --top-k 10
python -m ivy_agent_demo.memory_packet_cli diagnose-ranking --query "write outside sandbox policy" --policy safety_first --top-k 10
python -m ivy_agent_demo.memory_ranking_eval --cases ivy_agent_demo\memory_packet_ranking_cases.json --compare-latest
```

Expected: diagnostics include `source_family`, matched terms, and ranking scores. Ranking eval writes reports under `C:\ivy\runs\memory_ranking_eval`.
