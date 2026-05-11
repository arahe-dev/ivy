from __future__ import annotations

import argparse
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from generate_external_signal_recall_dataset import write_dataset
    from mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus
except ModuleNotFoundError:
    from scripts.generate_external_signal_recall_dataset import write_dataset
    from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "out" / "context_stress_external_signal_recall"
DEFAULT_OUT = ROOT / "docs" / "EXTERNAL_GENERALIZATION_GATE.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def summary_latency(summary: dict[str, Any], name: str) -> float:
    latency = summary.get("latency_ms", {})
    if isinstance(latency, dict):
        return float(latency.get(name, 0.0) or 0.0)
    return float(summary.get(f"{name}_latency_ms", 0.0) or 0.0)


def gate_status(summary: dict[str, Any], *, max_mean_latency_ms: float, max_p95_latency_ms: float) -> dict[str, Any]:
    latencies = [float(result.get("latency_ms", 0.0)) for result in summary.get("results", [])]
    p95 = max(latencies) if len(latencies) < 2 else statistics.quantiles(latencies, n=20, method="inclusive")[18]
    metrics = summary.get("evidence_metrics", {})
    checks = {
        "all_cases_pass": int(summary.get("passed", 0)) == int(summary.get("cases", 0)),
        "required_recall_perfect": float(metrics.get("required_recall", 0.0)) == 1.0,
        "required_only_precision_perfect": float(metrics.get("required_only_precision", 0.0)) == 1.0,
        "no_forbidden_hits": int(metrics.get("forbidden_hits", 0)) == 0,
        "mean_latency_under_budget": summary_latency(summary, "mean") <= max_mean_latency_ms,
        "p95_latency_under_budget": float(p95) <= max_p95_latency_ms,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "max_mean_latency_ms": max_mean_latency_ms,
        "max_p95_latency_ms": max_p95_latency_ms,
        "p95_latency_ms": round(float(p95), 3),
    }


def run_gate(dataset: Path, *, max_mean_latency_ms: float, max_p95_latency_ms: float) -> dict[str, Any]:
    manifest = write_dataset(dataset)
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset)
    summary = benchmark(router, load_cases(dataset), validate_artifacts=False)
    status = gate_status(summary, max_mean_latency_ms=max_mean_latency_ms, max_p95_latency_ms=max_p95_latency_ms)
    return {
        "schema_version": "mome_moce.external_generalization_gate.v0.1",
        "created_at": utc_now(),
        "dataset": str(dataset),
        "dataset_manifest": manifest,
        "summary": summary,
        "status": status,
    }


def write_report(gate: dict[str, Any], out: Path) -> None:
    summary = gate["summary"]
    status = gate["status"]
    metrics = summary.get("evidence_metrics", {})
    manifest = gate["dataset_manifest"]
    lines = [
        "# External Generalization Gate",
        "",
        f"Created: `{gate['created_at']}`",
        f"Gate passed: `{status['passed']}`",
        f"Dataset: `{manifest['dataset_id']}`",
        f"Corpus items: `{manifest['corpus_items']}`",
        f"Cases: `{summary['cases']}`",
        "",
        "## Why This Gate Exists",
        "",
        "This gate keeps the MoME/MoCE router honest against non-IVY product and architecture evidence.",
        "It uses the external Signal and Recall Board pack, including decoys and an unsupported commercial-pricing abstention case, so an internal IVY-only benchmark cannot hide overfitting.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Passed | `{summary['passed']} / {summary['cases']}` |",
        f"| Quality | `{summary['quality']:.4f}` |",
        f"| Required recall | `{metrics.get('required_recall', 0.0):.4f}` |",
        f"| Required-only precision | `{metrics.get('required_only_precision', 0.0):.4f}` |",
        f"| Forbidden hits | `{metrics.get('forbidden_hits', 0)}` |",
        f"| Avg selected | `{metrics.get('avg_selected', 0.0):.4f}` |",
        f"| Mean latency | `{summary_latency(summary, 'mean'):.3f} ms` |",
        f"| P50 latency | `{summary_latency(summary, 'p50'):.3f} ms` |",
        f"| P95 latency | `{status['p95_latency_ms']:.3f} ms` |",
        f"| Max latency | `{summary_latency(summary, 'max'):.3f} ms` |",
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for name, passed in status["checks"].items():
        lines.append(f"| `{name}` | `{passed}` |")
    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Case | Pass | Decision | Selected | Latency ms |",
            "|---|---:|---|---|---:|",
        ]
    )
    for result in summary.get("results", []):
        selected = ", ".join(result.get("selected_ids", []))
        lines.append(
            f"| `{result['case_id']}` | `{result['passed']}` | `{result['decision']}` | `{selected}` | `{result.get('latency_ms', 0.0):.3f}` |"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CP74 external Signal/Recall generalization gate.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--max-mean-latency-ms", type=float, default=2.0)
    parser.add_argument("--max-p95-latency-ms", type=float, default=5.0)
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    gate = run_gate(dataset, max_mean_latency_ms=args.max_mean_latency_ms, max_p95_latency_ms=args.max_p95_latency_ms)
    write_report(gate, args.out.resolve())
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "passed": gate["status"]["passed"],
                "report": str(args.out),
                "dataset": str(dataset),
                "summary": {
                    "passed": gate["summary"]["passed"],
                    "cases": gate["summary"]["cases"],
                    "quality": gate["summary"]["quality"],
                    "mean_latency_ms": summary_latency(gate["summary"], "mean"),
                    "p95_latency_ms": gate["status"]["p95_latency_ms"],
                },
            },
            indent=2,
        )
    )
    return 0 if gate["status"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
