from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUST_MANIFEST = ROOT / "rust" / "acca_index" / "Cargo.toml"


def load_cases(dataset: Path) -> list[dict[str, Any]]:
    return json.loads((dataset / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]


def run_rust_index(dataset: Path, *, top_k: int, release: bool) -> tuple[dict[str, Any], float]:
    cmd = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(RUST_MANIFEST),
    ]
    if release:
        cmd.append("--release")
    cmd.extend(
        [
            "--",
            "--corpus",
            str(dataset / "corpus" / "corpus_items.jsonl"),
            "--cases",
            str(dataset / "eval" / "cases.json"),
            "--top-k",
            str(top_k),
        ]
    )
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return json.loads(proc.stdout), elapsed_ms


def evaluate_candidate_recall(cases: list[dict[str, Any]], rust_payload: dict[str, Any]) -> dict[str, Any]:
    by_case = {result["case_id"]: result for result in rust_payload["results"]}
    rows = []
    required_total = 0
    required_hit_total = 0
    for case in cases:
        result = by_case[case["id"]]
        candidates = [candidate["id"] for candidate in result["candidates"]]
        required = list(case.get("required_source_ids", []))
        hits = [item_id for item_id in required if item_id in candidates]
        missing = [item_id for item_id in required if item_id not in candidates]
        required_total += len(required)
        required_hit_total += len(hits)
        rows.append(
            {
                "case_id": case["id"],
                "required": required,
                "hits": hits,
                "missing": missing,
                "candidate_count": result["candidate_count"],
                "top_candidates": candidates[:8],
            }
        )
    failures = [row for row in rows if row["missing"]]
    return {
        "cases": len(cases),
        "required_total": required_total,
        "required_hits": required_hit_total,
        "required_recall_at_k": round(required_hit_total / required_total, 6) if required_total else 1.0,
        "failed_cases": len(failures),
        "failures": failures,
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CP9 Rust candidate-index probe.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real")
    parser.add_argument("--top-k", type=int, default=32)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases = load_cases(dataset)
    rust_payload, elapsed_ms = run_rust_index(dataset, top_k=args.top_k, release=args.release)
    summary = evaluate_candidate_recall(cases, rust_payload)
    payload = {
        "runner_version": "cp9.rust_index_probe.v0.1",
        "dataset": str(dataset),
        "top_k": args.top_k,
        "release": args.release,
        "elapsed_ms": round(elapsed_ms, 3),
        "rust": rust_payload,
        "summary": summary,
    }
    output = args.output or ROOT / "out" / f"rust_index_probe_{dataset.name}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    printable = {key: summary[key] for key in ["cases", "required_total", "required_hits", "required_recall_at_k", "failed_cases"]}
    printable["elapsed_ms"] = round(elapsed_ms, 3)
    printable["output"] = str(output)
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if summary["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
