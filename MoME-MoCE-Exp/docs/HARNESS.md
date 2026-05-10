# MoME/MoCE Harness

`scripts/mome_moce_harness.py` benchmarks an evidence-routing harness over the generated context-stress datasets.

The intended split is:

- **MoCE / context experts**: deterministic gates for whether context is needed, which source families matter, and how to treat stale/decoy/conflict evidence.
- **MoME / memory experts**: sparse lexical memory, source-family memory, authority memory, strict identifier memory, and conflict-pair memory.
- **Local GGUF finder**: optional Qwen GGUF reranker over already-retrieved candidates. It is advisory only and cannot bypass deterministic MoCE authority/staleness/decoy gates.
- **Frontier model**: receives a compact `frontier_model_context_packet` and performs final synthesis. In this experiment, the harness measures whether the packet contains the expected evidence.

## Setup

The local virtualenv is:

```powershell
cd C:\ivy\MoME-MoCE-Exp
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install llama-cpp-python
```

The configured GGUF path is:

```text
C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf
```

## Fast deterministic benchmark

```powershell
.\.venv\Scripts\python.exe scripts\mome_moce_harness.py `
  --dataset out\context_stress_smoke `
  --mode deterministic `
  --output out\harness_smoke_deterministic.json
```

Repeat for:

```powershell
out\context_stress_medium
out\context_stress_stress
```

## GGUF load probe

```powershell
.\.venv\Scripts\python.exe scripts\mome_moce_harness.py `
  --dataset out\context_stress_smoke `
  --mode probe-model `
  --model "C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf" `
  --n-ctx 2048 `
  --n-threads 8
```

## Hybrid mode

Default hybrid mode calls the local model only for ambiguous routes:

```powershell
.\.venv\Scripts\python.exe scripts\mome_moce_harness.py `
  --dataset out\context_stress_smoke `
  --mode hybrid `
  --model "C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf" `
  --local-policy ambiguous `
  --output out\harness_smoke_hybrid_ambiguous.json
```

For stress-testing local-model behavior:

```powershell
.\.venv\Scripts\python.exe scripts\mome_moce_harness.py `
  --dataset out\context_stress_smoke `
  --mode hybrid `
  --model "C:\Users\arahe\Downloads\Qwen3-4B-Q4_K_M.gguf" `
  --force-local `
  --limit 8 `
  --output out\harness_smoke_hybrid_force_local_limit8.json
```

## Current finding

The Qwen3 4B Q4_K_M GGUF loads successfully through `llama-cpp-python`, but CPU inference is slow on this machine. The practical architecture is therefore:

1. use deterministic MoME/MoCE for the hot recall path;
2. use the local GGUF only as a bounded reranker for ambiguous candidate sets;
3. keep deterministic authority/staleness/decoy gates after local reranking;
4. hand the final compact packet to the frontier model for synthesis.

