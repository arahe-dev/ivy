from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from run_librarian_advisor_harness import DEFAULT_CASES, DEFAULT_OUT, resolve_path, run_harness
except ModuleNotFoundError:
    from scripts.run_librarian_advisor_harness import DEFAULT_CASES, DEFAULT_OUT, resolve_path, run_harness


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_OUT = ROOT / "out" / "librarian_strategy_matrix"
DEFAULT_STRATEGIES = ["rule", "dd-rule", "spec-dd", "spec-dd-lazy", "helper-lazy"]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def summarize_strategy(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [run["summary"] for run in runs]
    return {
        "runs": len(runs),
        "quality_mean": round(statistics.fmean(float(item["librarian_quality"]) for item in summaries), 4),
        "helped_cases": sorted({case for item in summaries for case in item["librarian_helped_cases"]}),
        "harmed_cases": sorted({case for item in summaries for case in item["librarian_harmed_cases"]}),
        "forbidden_hits_total": sum(int(item["forbidden_hits"]["librarian"]) for item in summaries),
        "latency_ms_mean": round(statistics.fmean(float(item["librarian_latency_ms_mean"]) for item in summaries), 3),
        "latency_ms_min": round(min(float(item["librarian_latency_ms_mean"]) for item in summaries), 3),
        "latency_ms_max": round(max(float(item["librarian_latency_ms_mean"]) for item in summaries), 3),
    }


def matrix_report(payload: dict[str, Any]) -> str:
    rows = [
        "# D-ACCA Librarian Strategy Matrix",
        "",
        f"Created: {payload['created_at']}",
        f"Repeats: {payload['repeats']}",
        "",
        "| strategy | quality mean | helped | harmed | forbidden hits | latency mean ms | latency min/max ms |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for strategy, summary in payload["strategies"].items():
        rows.append(
            "| {strategy} | {quality:.4f} | {helped} | {harmed} | {forbidden} | {latency:.3f} | {lat_min:.3f}/{lat_max:.3f} |".format(
                strategy=strategy,
                quality=summary["quality_mean"],
                helped=len(summary["helped_cases"]),
                harmed=len(summary["harmed_cases"]),
                forbidden=summary["forbidden_hits_total"],
                latency=summary["latency_ms_mean"],
                lat_min=summary["latency_ms_min"],
                lat_max=summary["latency_ms_max"],
            )
        )
    return "\n".join(rows) + "\n"


def run_matrix(
    *,
    cases_path: Path,
    out_dir: Path,
    strategies: list[str],
    repeats: int,
    candidate_backend: str,
    top_k: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    strategy_runs: dict[str, list[dict[str, Any]]] = {}
    for strategy in strategies:
        runs = []
        for repeat in range(1, repeats + 1):
            run_out = out_dir / "runs" / strategy / f"repeat_{repeat:02d}"
            runs.append(
                run_harness(
                    cases_path=cases_path,
                    out_dir=run_out,
                    default_dataset=Path("out/context_stress_ivy_real_v2"),
                    strategy=strategy,
                    candidate_backend=candidate_backend,
                    top_k=top_k,
                    max_union_items=3,
                    limit=None,
                    write_artifacts=False,
                )
            )
        strategy_runs[strategy] = runs

    payload = {
        "runner_version": "d_acca.librarian_strategy_matrix.v0.1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cases_path": str(cases_path),
        "strategies": {strategy: summarize_strategy(runs) for strategy, runs in strategy_runs.items()},
        "repeats": repeats,
        "candidate_backend": candidate_backend,
        "top_k": top_k,
    }
    write_json(out_dir / "librarian_strategy_matrix.json", payload)
    write_text(out_dir / "librarian_strategy_matrix.md", matrix_report(payload))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run repeated deterministic librarian strategy comparisons.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_MATRIX_OUT)
    parser.add_argument("--strategies", nargs="+", default=DEFAULT_STRATEGIES)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--candidate-backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)

    payload = run_matrix(
        cases_path=resolve_path(args.cases),
        out_dir=resolve_path(args.out),
        strategies=args.strategies,
        repeats=args.repeats,
        candidate_backend=args.candidate_backend,
        top_k=args.top_k,
    )
    print(json.dumps(payload["strategies"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
