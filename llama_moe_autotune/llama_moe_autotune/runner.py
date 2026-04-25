from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .candidates import Candidate, build_candidate_command
from .system_probe import (
    collect_process_peak_memory,
    get_available_ram_bytes,
    gpu_memory_snapshot,
)
from .util import command_to_string


OOM_PATTERNS = [
    "out of memory",
    "cuda out of memory",
    "cuda malloc failed",
    "failed to allocate",
    "not enough memory",
    "bad allocation",
]

UNSUPPORTED_PATTERNS = [
    "unknown argument",
    "invalid argument",
    "unrecognized option",
    "unknown option",
]


def run_candidate(
    candidate: Candidate,
    llama_cli: Path,
    model: Path,
    prompt: str,
    supported_flags: dict[str, Any],
    raw_logs_dir: Path,
    timeout_seconds: int,
    seed: int = 12345,
    disable_reasoning: bool = False,
) -> dict[str, Any]:
    raw_logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = raw_logs_dir / f"candidate_{candidate.index:03d}_stdout.txt"
    stderr_path = raw_logs_dir / f"candidate_{candidate.index:03d}_stderr.txt"
    command = build_candidate_command(
        candidate,
        llama_cli,
        model,
        prompt,
        supported_flags,
        seed=seed,
        disable_reasoning=disable_reasoning,
    )
    available_ram_before = get_available_ram_bytes()
    gpu_before = gpu_memory_snapshot()
    started = time.perf_counter()
    peak_memory: dict[str, Any] = {}
    timed_out = False
    exit_code: int | None = None

    with (
        stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file,
        stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_file,
    ):
        try:
            proc = subprocess.Popen(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            deadline = time.perf_counter() + timeout_seconds
            while proc.poll() is None:
                peak_memory = collect_process_peak_memory(proc.pid)
                if time.perf_counter() > deadline:
                    timed_out = True
                    proc.kill()
                    break
                time.sleep(0.5)
            exit_code = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = None
        except Exception as exc:
            stderr_file.write(f"\nrunner exception: {exc}\n")
            exit_code = -1

    wall_seconds = time.perf_counter() - started
    stdout_text = _read_tail(stdout_path)
    stderr_text = _read_tail(stderr_path)
    parsed = parse_llama_metrics(stdout_text + "\n" + stderr_text)
    outcome = classify_outcome(exit_code, timed_out, stdout_text, stderr_text, parsed)
    estimated = False
    decode_tps = parsed.get("decode_tps")
    if decode_tps is None and outcome == "success" and wall_seconds > 0:
        decode_tps = candidate.n_predict / wall_seconds
        estimated = True

    return {
        "candidate": candidate.to_dict(),
        "command": command,
        "command_string": command_to_string(command),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "wall_seconds": round(wall_seconds, 3),
        "available_ram_before_bytes": available_ram_before,
        "gpu_before": gpu_before,
        "gpu_after": gpu_memory_snapshot(),
        "peak_process_memory": peak_memory,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "metrics": parsed,
        "decode_tps": decode_tps,
        "decode_tps_estimated": estimated,
        "outcome": outcome,
    }


def parse_llama_metrics(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    patterns = {
        "prompt_tps": r"prompt eval time\s*=\s*.*?/\s*[\d.]+\s*tokens per second\s*\)?|prompt_per_second[\"']?\s*[:=]\s*([\d.]+)",
        "decode_tps": r"eval time\s*=\s*.*?/\s*([\d.]+)\s*tokens per second|predicted_per_second[\"']?\s*[:=]\s*([\d.]+)",
        "total_tps": r"total time\s*=\s*.*?/\s*([\d.]+)\s*tokens per second",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            values = [group for group in match.groups() if group]
            if values:
                metrics[name] = _float_or_none(values[-1])

    prompt_match = re.search(
        r"prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens", text, re.I
    )
    eval_match = re.search(
        r"eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*runs", text, re.I
    )
    if prompt_match:
        metrics["prompt_ms"] = _float_or_none(prompt_match.group(1))
        metrics["prompt_n"] = int(prompt_match.group(2))
    if eval_match:
        metrics["predicted_ms"] = _float_or_none(eval_match.group(1))
        metrics["predicted_n"] = int(eval_match.group(2))
    return metrics


def classify_outcome(
    exit_code: int | None,
    timed_out: bool,
    stdout_text: str,
    stderr_text: str,
    parsed: dict[str, Any],
) -> str:
    text = (stdout_text + "\n" + stderr_text).lower()
    if timed_out:
        return "timeout"
    if any(pattern in text for pattern in OOM_PATTERNS):
        return "out of memory"
    if any(pattern in text for pattern in UNSUPPORTED_PATTERNS):
        return "unsupported flag"
    if exit_code not in (0, None):
        return "crash"
    if exit_code == 0 and parsed:
        return "success"
    if exit_code == 0:
        return "parse failure but command completed"
    return "crash"


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _read_tail(path: Path, max_chars: int = 50000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return text[-max_chars:]
