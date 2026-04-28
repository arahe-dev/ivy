#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path


FIELDS = [
    "config_name",
    "model_id",
    "ctx",
    "cache_k",
    "cache_v",
    "cpu_moe",
    "n_gpu_layers",
    "prompt_name",
    "http_success",
    "load_start_failure",
    "prompt_ms",
    "predicted_ms",
    "predicted_n",
    "decode_tps",
    "wall_ms",
    "first_token_ms",
    "json_valid",
    "error_message",
    "run_dir",
]


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def nested(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def infer_model_id(model_path):
    if not model_path:
        return None
    name = Path(str(model_path)).name
    return name or str(model_path)


def response_content(resp):
    if not isinstance(resp, dict):
        return ""
    if isinstance(resp.get("content"), str):
        return resp["content"]
    choices = resp.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
        if isinstance(choices[0].get("text"), str):
            return choices[0]["text"]
    return ""


def strict_json_valid(text):
    try:
        json.loads(text.strip())
        return True
    except Exception:
        return False


def parse_run(run_dir):
    config = read_json(run_dir / "config.json") or {}
    result = read_json(run_dir / "result.json") or {}
    failure = read_json(run_dir / "failure.json") or {}
    response = read_json(run_dir / "response.json") or {}

    timings = response.get("timings") if isinstance(response, dict) else None
    if not isinstance(timings, dict):
        timings = {}

    predicted_ms = timings.get("predicted_ms")
    predicted_n = timings.get("predicted_n")
    decode_tps = timings.get("predicted_per_second")
    if decode_tps is None and predicted_ms and predicted_n:
        try:
            decode_tps = round(float(predicted_n) * 1000.0 / float(predicted_ms), 3)
        except Exception:
            decode_tps = None

    prompt_name = config.get("prompt_name")
    content = response_content(response)
    json_valid = None
    if prompt_name == "json_tool_call":
        json_valid = strict_json_valid(content)

    error_message = failure.get("error") or result.get("error")
    http_success = bool(result.get("http_success")) if "http_success" in result else bool(response)
    load_start_failure = bool(failure.get("load_start_failure"))
    if error_message and not response:
        load_start_failure = True

    return {
        "config_name": config.get("config_name") or run_dir.name,
        "model_id": infer_model_id(config.get("model_path")),
        "ctx": config.get("ctx"),
        "cache_k": config.get("cache_k"),
        "cache_v": config.get("cache_v"),
        "cpu_moe": config.get("cpu_moe"),
        "n_gpu_layers": config.get("n_gpu_layers"),
        "prompt_name": prompt_name,
        "http_success": http_success,
        "load_start_failure": load_start_failure,
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": predicted_ms,
        "predicted_n": predicted_n,
        "decode_tps": decode_tps,
        "wall_ms": result.get("wall_ms"),
        "first_token_ms": timings.get("predicted_per_token_ms") or timings.get("first_token_ms"),
        "json_valid": json_valid,
        "error_message": error_message,
        "run_dir": str(run_dir),
    }


def write_report(rows, out_path):
    ok = sum(1 for r in rows if r["http_success"])
    failed = len(rows) - ok
    json_rows = [r for r in rows if r["prompt_name"] == "json_tool_call"]
    json_ok = sum(1 for r in json_rows if r["json_valid"] is True)
    lines = [
        "# Qwen 3.6 35B-A3B RTX 4060 Phase 1 Report",
        "",
        f"- Total runs: {len(rows)}",
        f"- HTTP successes: {ok}",
        f"- Failures: {failed}",
        f"- JSON prompt valid: {json_ok}/{len(json_rows)}",
        "",
        "## Runs",
        "",
        "| config | prompt | ctx | cache_k | cache_v | cpu_moe | n_gpu_layers | success | decode_tps | wall_ms | error |",
        "|---|---|---:|---|---|---|---:|---|---:|---:|---|",
    ]
    for r in rows:
        err = (r.get("error_message") or "").replace("|", "\\|")
        if len(err) > 120:
            err = err[:117] + "..."
        lines.append(
            f"| {r['config_name']} | {r.get('prompt_name') or ''} | {r.get('ctx') or ''} | "
            f"{r.get('cache_k') or ''} | {r.get('cache_v') or ''} | {r.get('cpu_moe')} | "
            f"{r.get('n_gpu_layers') or ''} | {r.get('http_success')} | {r.get('decode_tps') or ''} | "
            f"{r.get('wall_ms') or ''} | {err} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Collect Qwen 3.6 4060 benchmark metrics.")
    ap.add_argument("run_root", help="Timestamped run directory under runs/qwen36_4060_bench")
    args = ap.parse_args()

    root = Path(args.run_root)
    if not root.exists():
        raise SystemExit(f"Run root not found: {root}")

    run_dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "config.json").exists())
    rows = [parse_run(p) for p in run_dirs]

    csv_path = root / "summary.csv"
    json_path = root / "summary.json"
    report_path = root / "report.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_report(rows, report_path)
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
