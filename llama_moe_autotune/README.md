# llama_moe_autotune

Windows-first `llama.cpp` wrapper/profiler for huge MoE GGUF models. It does not modify `llama.cpp`, change OS settings, or tune pagefile/registry/CUDA. It generates bounded candidate commands, runs them with timeouts, parses llama.cpp timing output where possible, ranks successful configs, and writes reproducible launch scripts.

## Basic use

```powershell
python -m llama_moe_autotune `
  --llama-cli "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-cli.exe" `
  --model "C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf" `
  --prompt "Write one short paragraph about local LLMs." `
  --out ".\autotune_runs" `
  --max-candidates 40 `
  --max-seconds-per-run 180
```

## Dry run

```powershell
python -m llama_moe_autotune `
  --llama-cli "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-cli.exe" `
  --model "C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf" `
  --dry-run
```

Dry run writes planning artifacts but does not launch benchmark candidates.

## Outputs

The tool writes:

- `autotune_runs/latest/system_info.json`
- `autotune_runs/latest/model_info.json`
- `autotune_runs/latest/supported_flags.json`
- `autotune_runs/latest/candidates.json`
- `autotune_runs/latest/results.json`
- `autotune_runs/latest/ranked_results.md`
- `autotune_runs/latest/best_config.json`
- `autotune_runs/latest/launch_best.bat`
- `autotune_runs/latest/launch_safe.bat`
- `autotune_runs/latest/override_plans.md`
- `autotune_runs/latest/raw_logs/candidate_000_stdout.txt`
- `autotune_runs/latest/raw_logs/candidate_000_stderr.txt`

## Candidate policy

The first candidate is a conservative survival smoke test:

```text
llama-cli -m MODEL -p PROMPT --mmap -ngl 0 --cpu-moe -c 512 -b 32 -ub 16 -ctk q4_0 -ctv q4_0 -n 16
```

Only flags detected in `llama-cli --help` are emitted. Unsupported flags are recorded in the report.

## Safety

The tool will not download models, modify pagefile settings, edit the registry, install CUDA, rebuild `llama.cpp`, delete user files, run more than `--max-candidates`, or exceed `--max-seconds-per-run` for a candidate.
