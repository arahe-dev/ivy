from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus


ROOT = Path(__file__).resolve().parents[1]


def run_latency_gate(
    dataset: Path,
    *,
    backend: str = "indexed",
    min_quality: float = 0.9,
    max_forbidden_hits: int = 0,
    max_mean_ms: float = 5.0,
    max_p50_ms: float = 5.0,
    max_worst_ms: float = 10.0,
) -> dict[str, Any]:
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend=backend, dataset_path=dataset)
    summary = benchmark(router, load_cases(dataset), validate_artifacts=False)
    latency = summary["latency_ms"]
    evidence = summary["evidence_metrics"]
    checks = {
        "quality": summary["quality"] >= min_quality,
        "forbidden_hits": evidence["forbidden_hits"] <= max_forbidden_hits,
        "mean_latency_ms": latency["mean"] <= max_mean_ms,
        "p50_latency_ms": latency["p50"] <= max_p50_ms,
        "worst_latency_ms": latency["max"] <= max_worst_ms,
    }
    return {
        "dataset": str(dataset),
        "backend": backend,
        "thresholds": {
            "min_quality": min_quality,
            "max_forbidden_hits": max_forbidden_hits,
            "max_mean_ms": max_mean_ms,
            "max_p50_ms": max_p50_ms,
            "max_worst_ms": max_worst_ms,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "summary": summary,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    latency = summary["latency_ms"]
    evidence = summary["evidence_metrics"]
    thresholds = payload["thresholds"]
    lines = [
        "# CP12 Latency Gate",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Backend: `{payload['backend']}`",
        f"- Result: `{'PASS' if payload['passed'] else 'FAIL'}`",
        "",
        "## Quality",
        "",
        f"- Cases: {summary['passed']}/{summary['cases']}",
        f"- Quality: {summary['quality']:.4f} (threshold >= {thresholds['min_quality']:.4f})",
        f"- Required recall: {evidence['required_recall']:.4f}",
        f"- Forbidden hits: {evidence['forbidden_hits']} (threshold <= {thresholds['max_forbidden_hits']})",
        "",
        "## Latency",
        "",
        "| Metric | Observed ms | Threshold ms | Pass |",
        "|---|---:|---:|---|",
        f"| Mean | {latency['mean']:.3f} | {thresholds['max_mean_ms']:.3f} | {payload['checks']['mean_latency_ms']} |",
        f"| P50 | {latency['p50']:.3f} | {thresholds['max_p50_ms']:.3f} | {payload['checks']['p50_latency_ms']} |",
        f"| Worst | {latency['max']:.3f} | {thresholds['max_worst_ms']:.3f} | {payload['checks']['worst_latency_ms']} |",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CP12 deterministic router latency gate.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real_v3")
    parser.add_argument("--backend", default="indexed")
    parser.add_argument("--min-quality", type=float, default=0.9)
    parser.add_argument("--max-forbidden-hits", type=int, default=0)
    parser.add_argument("--max-mean-ms", type=float, default=5.0)
    parser.add_argument("--max-p50-ms", type=float, default=5.0)
    parser.add_argument("--max-worst-ms", type=float, default=10.0)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    payload = run_latency_gate(
        args.dataset,
        backend=args.backend,
        min_quality=args.min_quality,
        max_forbidden_hits=args.max_forbidden_hits,
        max_mean_ms=args.max_mean_ms,
        max_p50_ms=args.max_p50_ms,
        max_worst_ms=args.max_worst_ms,
    )
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.output_md:
        write_markdown(payload, args.output_md)
    print(json.dumps(payload, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
