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


def latency_p95(summary: dict[str, Any]) -> float:
    latencies = [float(result.get("latency_ms", 0.0)) for result in summary.get("results", [])]
    return max(latencies) if len(latencies) < 2 else statistics.quantiles(latencies, n=20, method="inclusive")[18]


def summary_checks(summary: dict[str, Any], *, max_mean_latency_ms: float, max_p95_latency_ms: float, prefix: str = "") -> dict[str, bool]:
    p95 = latency_p95(summary)
    metrics = summary.get("evidence_metrics", {})
    return {
        f"{prefix}all_cases_pass": int(summary.get("passed", 0)) == int(summary.get("cases", 0)),
        f"{prefix}required_recall_perfect": float(metrics.get("required_recall", 0.0)) == 1.0,
        f"{prefix}required_only_precision_perfect": float(metrics.get("required_only_precision", 0.0)) == 1.0,
        f"{prefix}no_forbidden_hits": int(metrics.get("forbidden_hits", 0)) == 0,
        f"{prefix}mean_latency_under_budget": summary_latency(summary, "mean") <= max_mean_latency_ms,
        f"{prefix}p95_latency_under_budget": float(p95) <= max_p95_latency_ms,
    }


def gate_status(
    summary: dict[str, Any],
    *,
    max_mean_latency_ms: float,
    max_p95_latency_ms: float,
    no_exact_anchor_ablation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p95 = latency_p95(summary)
    checks = summary_checks(summary, max_mean_latency_ms=max_mean_latency_ms, max_p95_latency_ms=max_p95_latency_ms)
    ablation_p95 = None
    if no_exact_anchor_ablation is not None:
        ablation_p95 = latency_p95(no_exact_anchor_ablation)
        checks.update(
            summary_checks(
                no_exact_anchor_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="no_exact_anchor_",
            )
        )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "max_mean_latency_ms": max_mean_latency_ms,
        "max_p95_latency_ms": max_p95_latency_ms,
        "p95_latency_ms": round(float(p95), 3),
        "no_exact_anchor_p95_latency_ms": None if ablation_p95 is None else round(float(ablation_p95), 3),
    }


def run_summary(dataset: Path, *, disabled_experts: set[str] | None = None) -> dict[str, Any]:
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset, disabled_experts=disabled_experts)
    return benchmark(router, load_cases(dataset), validate_artifacts=False)


def run_gate(
    dataset: Path,
    *,
    max_mean_latency_ms: float,
    max_p95_latency_ms: float,
    include_no_exact_anchor_ablation: bool = True,
) -> dict[str, Any]:
    manifest = write_dataset(dataset)
    summary = run_summary(dataset)
    no_exact_anchor_ablation = run_summary(dataset, disabled_experts={"exact_anchor_memory"}) if include_no_exact_anchor_ablation else None
    status = gate_status(
        summary,
        max_mean_latency_ms=max_mean_latency_ms,
        max_p95_latency_ms=max_p95_latency_ms,
        no_exact_anchor_ablation=no_exact_anchor_ablation,
    )
    return {
        "schema_version": "mome_moce.external_generalization_gate.v0.1",
        "created_at": utc_now(),
        "dataset": str(dataset),
        "dataset_manifest": manifest,
        "summary": summary,
        "no_exact_anchor_ablation": no_exact_anchor_ablation,
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
    if gate.get("no_exact_anchor_ablation") is not None:
        ablation = gate["no_exact_anchor_ablation"]
        ablation_metrics = ablation.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## No Exact Anchor Ablation",
                "",
                "This reruns the same external cases with `exact_anchor_memory` disabled. Passing it means the gate is not solely dependent on the exact-anchor expert.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{ablation['passed']} / {ablation['cases']}` |",
                f"| Quality | `{ablation['quality']:.4f}` |",
                f"| Required recall | `{ablation_metrics.get('required_recall', 0.0):.4f}` |",
                f"| Required-only precision | `{ablation_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Forbidden hits | `{ablation_metrics.get('forbidden_hits', 0)}` |",
                f"| Mean latency | `{summary_latency(ablation, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['no_exact_anchor_p95_latency_ms']:.3f} ms` |",
            ]
        )
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
    parser.add_argument("--skip-no-exact-anchor-ablation", action="store_true")
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    gate = run_gate(
        dataset,
        max_mean_latency_ms=args.max_mean_latency_ms,
        max_p95_latency_ms=args.max_p95_latency_ms,
        include_no_exact_anchor_ablation=not args.skip_no_exact_anchor_ablation,
    )
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
                    "no_exact_anchor_passed": None
                    if gate.get("no_exact_anchor_ablation") is None
                    else gate["no_exact_anchor_ablation"]["passed"],
                    "no_exact_anchor_p95_latency_ms": gate["status"]["no_exact_anchor_p95_latency_ms"],
                },
            },
            indent=2,
        )
    )
    return 0 if gate["status"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
