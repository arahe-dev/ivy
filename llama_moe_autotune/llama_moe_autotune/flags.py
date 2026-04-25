from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


FLAG_ALIASES = {
    "--mmap": ["--mmap"],
    "--direct-io": ["--direct-io"],
    "--cpu-moe": ["--cpu-moe"],
    "--n-cpu-moe": ["--n-cpu-moe"],
    "--override-tensor": ["--override-tensor"],
    "-ctk": ["-ctk", "--cache-type-k"],
    "-ctv": ["-ctv", "--cache-type-v"],
    "-ub": ["-ub", "--ubatch-size"],
    "-ngl": ["-ngl", "--n-gpu-layers"],
    "--fit": ["--fit"],
    "--fit-target": ["--fit-target"],
    "--fit-ctx": ["--fit-ctx"],
    "--seed": ["--seed", "-s"],
    "--reasoning-budget": ["--reasoning-budget"],
    "--single-turn": ["--single-turn"],
    "--no-display-prompt": ["--no-display-prompt"],
}


def detect_supported_flags(llama_cli: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "llama_cli": str(llama_cli),
        "supported": {},
        "unsupported": [],
        "help_exit_code": None,
        "help_excerpt": "",
        "warnings": [],
    }
    if not llama_cli.exists():
        result["error"] = f"llama-cli does not exist: {llama_cli}"
        return result
    try:
        proc = subprocess.run(
            [str(llama_cli), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        text = f"{proc.stdout}\n{proc.stderr}"
        result["help_exit_code"] = proc.returncode
        result["help_excerpt"] = text[:8000]
    except Exception as exc:
        result["error"] = str(exc)
        text = ""

    for canonical, aliases in FLAG_ALIASES.items():
        found = any(_contains_flag(text, alias) for alias in aliases)
        result["supported"][canonical] = found
        if not found:
            result["unsupported"].append(canonical)
    result["n_gpu_layers_values"] = _n_gpu_layers_values(text)
    return result


def _contains_flag(help_text: str, flag: str) -> bool:
    return re.search(rf"(^|\s){re.escape(flag)}([,\s=<]|$)", help_text) is not None


def is_supported(flags: dict[str, Any], flag: str) -> bool:
    return bool(flags.get("supported", {}).get(flag, False))


def _n_gpu_layers_values(help_text: str) -> dict[str, bool]:
    lines = help_text.splitlines()
    relevant = []
    for index, line in enumerate(lines):
        if "--n-gpu-layers" in line or "--gpu-layers" in line or "-ngl" in line:
            relevant.extend(lines[index : index + 3])
    text = "\n".join(relevant).lower()
    return {
        "numeric": bool(relevant),
        "auto": "auto" in text,
        "all": "all" in text,
    }
