from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / "out" / "provider_certification_matrix"


def certification_decision(
    summary_by_suite: dict[str, Any],
    *,
    min_contract_json: float = 0.98,
    min_native_tools: float = 0.95,
) -> dict[str, Any]:
    contract = summary_by_suite.get("contract_json") or {}
    native = summary_by_suite.get("native_tools") or {}
    checks = {
        "contract_json_pass_rate": float(contract.get("pass_rate", 0.0)) >= min_contract_json,
        "native_tool_pass_rate": float(native.get("pass_rate", 0.0)) >= min_native_tools,
        "invalid_json_zero": int(contract.get("invalid_json", 0)) == 0 and int(native.get("invalid_json", 0)) == 0,
        "wrong_tool_zero": int(contract.get("wrong_tool", 0)) == 0 and int(native.get("wrong_tool", 0)) == 0,
        "think_tags_zero": int(contract.get("think_tags", 0)) == 0 and int(native.get("think_tags", 0)) == 0,
    }
    return {"certified": all(checks.values()), "checks": checks}


def _extract_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        raise ValueError("provider eval did not emit JSON")
    return json.loads(stdout[start : end + 1])


def run_model_eval(args: argparse.Namespace, model: str, out_root: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_opencode_go_tool_json_eval.py"),
        "--model",
        model,
        "--suite",
        "both",
        "--prompt-style",
        args.prompt_style,
        "--max-output-tokens",
        str(args.max_output_tokens),
        "--case-retries",
        str(args.case_retries),
        "--out-root",
        str(out_root / model.replace("/", "__").replace(":", "__")),
    ]
    if args.keep_proxy:
        command.append("--keep-proxy")
    start = time.perf_counter()
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=args.timeout_sec)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    row: dict[str, Any] = {
        "model": model,
        "command": command,
        "returncode": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    if proc.returncode == 0:
        payload = _extract_json(proc.stdout)
        row.update(payload)
        row.update(certification_decision(payload.get("summary_by_suite") or {}))
    else:
        row["certified"] = False
        row["checks"] = {"process_returncode_zero": False}
    return row


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# CP20 Provider Certification Matrix",
        "",
        "| Model | Certified | Contract | Native | Invalid JSON | Wrong Tool | Think Tags | Elapsed ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        suites = row.get("summary_by_suite") or {}
        contract = suites.get("contract_json") or {}
        native = suites.get("native_tools") or {}
        invalid = int(contract.get("invalid_json", 0)) + int(native.get("invalid_json", 0))
        wrong = int(contract.get("wrong_tool", 0)) + int(native.get("wrong_tool", 0))
        think = int(contract.get("think_tags", 0)) + int(native.get("think_tags", 0))
        lines.append(
            f"| `{row['model']}` | {row.get('certified')} | {float(contract.get('pass_rate', 0.0)):.3f} | "
            f"{float(native.get('pass_rate', 0.0)):.3f} | {invalid} | {wrong} | {think} | {row.get('elapsed_ms')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    out_root = args.out_root
    out_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if args.dry_run:
        for model in args.models:
            rows.append({"model": model, "certified": False, "checks": {"dry_run": True}, "elapsed_ms": 0})
    else:
        for model in args.models:
            rows.append(run_model_eval(args, model, out_root))
    payload = {
        "models": args.models,
        "rows": rows,
        "certified_models": [row["model"] for row in rows if row.get("certified")],
    }
    (out_root / "provider_certification_matrix.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(rows, out_root / "provider_certification_matrix.md")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OpenCode/OpenRouter provider certification for ACCA advisory use.")
    parser.add_argument("--models", nargs="+", default=["deepseek-v4-flash"])
    parser.add_argument("--prompt-style", choices=["base", "fewshot", "compact"], default="fewshot")
    parser.add_argument("--max-output-tokens", type=int, default=384)
    parser.add_argument("--case-retries", type=int, default=1)
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--keep-proxy", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_matrix(args), indent=2))


if __name__ == "__main__":
    main()
