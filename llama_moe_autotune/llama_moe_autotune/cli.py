from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from .candidates import build_candidate_command, generate_candidates
from .flags import detect_supported_flags, is_supported
from .gguf_probe import inspect_gguf
from .report import write_all_reports
from .runner import run_candidate
from .system_probe import collect_system_info
from .util import command_to_string, sanitize_name, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m llama_moe_autotune",
        description="Bounded llama.cpp MoE autotuner and profiler for huge GGUF models.",
    )
    parser.add_argument(
        "--llama-cli", required=True, help="Path to llama-cli executable."
    )
    parser.add_argument(
        "--model", required=True, help="Path to GGUF model or first split shard."
    )
    parser.add_argument(
        "--prompt",
        default="Write one short paragraph about local LLMs.",
        help="Benchmark prompt.",
    )
    parser.add_argument("--out", default="autotune_runs", help="Output directory.")
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=40,
        help="Maximum candidate commands to run or emit.",
    )
    parser.add_argument(
        "--max-seconds-per-run", type=int, default=180, help="Timeout per candidate."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan and report without running benchmark commands.",
    )
    parser.add_argument(
        "--n-predict",
        type=int,
        default=32,
        help="Tokens to generate per benchmark candidate.",
    )
    parser.add_argument(
        "--seed", type=int, default=12345, help="Seed when supported by llama.cpp."
    )
    parser.add_argument(
        "--disable-reasoning",
        action="store_true",
        default=None,
        help="Disable thinking/reasoning tokens (adds --reasoning-budget 0). Default: auto for MiniMax/Qwen/DeepSeek.",
    )
    parser.add_argument(
        "--allow-reasoning",
        action="store_true",
        help="Allow thinking/reasoning tokens (overrides --disable-reasoning).",
    )
    parser.add_argument(
        "--experiment",
        choices=["default", "post_reasoning_tune"],
        default="default",
        help="Experiment mode: default=standard, post_reasoning_tune=focused search.",
    )
    return parser


def _should_disable_reasoning(model: Path) -> bool:
    name_lower = model.name.lower()
    triggers = ["minimax", "qwen", "deepseek"]
    return any(trigger in name_lower for trigger in triggers)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    llama_cli = Path(args.llama_cli)
    model = Path(args.model)
    out_root = Path(args.out)
    latest = out_root / "latest"
    raw_logs = latest / "raw_logs"
    latest.mkdir(parents=True, exist_ok=True)
    raw_logs.mkdir(parents=True, exist_ok=True)

    if args.max_candidates < 1:
        parser.error("--max-candidates must be at least 1")
    if args.max_seconds_per_run < 1:
        parser.error("--max-seconds-per-run must be at least 1")
    if not llama_cli.exists():
        print(f"error: llama-cli path does not exist: {llama_cli}", file=sys.stderr)
        write_json(
            latest / "error.json",
            {"error": "llama-cli missing", "expected_path": str(llama_cli)},
        )
        return 2
    if not model.exists():
        print(f"error: model path does not exist: {model}", file=sys.stderr)
        write_json(
            latest / "error.json",
            {"error": "model missing", "expected_path": str(model)},
        )
        return 2

    if args.allow_reasoning:
        disable_reasoning = False
    elif args.disable_reasoning is not None:
        disable_reasoning = args.disable_reasoning
    else:
        disable_reasoning = _should_disable_reasoning(model)

    system_info = collect_system_info(llama_cli, model, latest)
    model_info = inspect_gguf(model)
    supported_flags = detect_supported_flags(llama_cli)

    reasoning_behavior = {
        "disable_reasoning": disable_reasoning,
        "supported": is_supported(supported_flags, "--reasoning-budget"),
        "model_based": args.disable_reasoning is None and not args.allow_reasoning,
    }

    candidates = generate_candidates(
        supported_flags,
        model_info,
        max_candidates=args.max_candidates,
        n_predict=args.n_predict,
        experiment=args.experiment,
        disable_reasoning=disable_reasoning,
    )
    candidate_dicts = []
    for candidate in candidates:
        command = build_candidate_command(
            candidate,
            llama_cli,
            model,
            args.prompt,
            supported_flags,
            seed=args.seed,
            disable_reasoning=disable_reasoning,
        )
        data = candidate.to_dict()
        data["command"] = command
        data["command_string"] = command_to_string(command)
        data["reasoning_disabled"] = disable_reasoning
        candidate_dicts.append(data)

    results = []
    if not args.dry_run:
        for candidate in candidates:
            result = run_candidate(
                candidate,
                llama_cli,
                model,
                args.prompt,
                supported_flags,
                raw_logs,
                timeout_seconds=args.max_seconds_per_run,
                seed=args.seed,
                disable_reasoning=disable_reasoning,
            )
            results.append(result)
            write_json(latest / "results.json", results)

    write_all_reports(
        latest,
        system_info,
        model_info,
        supported_flags,
        candidate_dicts,
        results,
        args.dry_run,
        reasoning_behavior,
    )

    run_manifest = {
        "created_unix": time.time(),
        "dry_run": args.dry_run,
        "llama_cli": str(llama_cli),
        "model": str(model),
        "out": str(latest),
        "max_candidates": args.max_candidates,
        "max_seconds_per_run": args.max_seconds_per_run,
        "experiment": args.experiment,
        "reasoning_behavior": reasoning_behavior,
    }
    write_json(latest / "run_manifest.json", run_manifest)

    mode = "dry run" if args.dry_run else "benchmark"
    print(f"{mode} complete: {latest}")
    print(f"ranked report: {latest / 'ranked_results.md'}")
    if disable_reasoning and is_supported(supported_flags, "--reasoning-budget"):
        print("reasoning disabled: --reasoning-budget 0 injected into all candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
