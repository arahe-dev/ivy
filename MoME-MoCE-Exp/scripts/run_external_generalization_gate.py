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

SEMANTIC_PARAPHRASES = {
    "cp23_signal_iphone_without_vps": "For the Signal phone bridge, what private delivery path reaches iOS without renting a public server?",
    "cp23_signal_not_codex_cloud": "Is the Signal phone bridge a hosted cloud broker tied only to Codex?",
    "cp23_signal_durable_coordination_primitive": "For Signal, what durable local record is treated as the coordination source of truth?",
    "cp23_signal_daemon_shell_boundary": "In Signal, should the notification daemon itself run arbitrary shell work from a phone response?",
    "cp23_recall_screenshot_free_context": "In Recall Board, what machine-readable export lets an AI inspect a board without screenshots?",
    "cp23_recall_text_graph_contents": "What compact graph representation does Recall Board produce from visible board structure?",
    "cp23_recall_graph_ir_role": "In Recall Board, what role does Graph IR play between AI semantics and the editable canvas?",
    "cp23_recall_second_brain_features": "Which Recall Board capabilities make it function more like a personal knowledge workspace than a plain drawing board?",
    "cp23_recall_cloud_price_abstain": "What is the current subscription price for Recall Cloud?",
}

NEGATIVE_CONTROL_QUERIES = {
    "neg_signal_android_play_store_release": "What is the latest Android Play Store release version for Signal bridge?",
    "neg_signal_hosted_sla": "What hosted uptime SLA does Signal provide for customers?",
    "neg_recall_cloud_price": "What is the current monthly subscription price for Recall Cloud?",
    "neg_recall_mobile_app_release": "When did Recall Board ship its production iOS app?",
    "neg_recall_soc2": "Does Recall Board have current SOC 2 certification?",
}


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
    semantic_paraphrase_ablation: dict[str, Any] | None = None,
    semantic_no_exact_anchor_ablation: dict[str, Any] | None = None,
    negative_control_ablation: dict[str, Any] | None = None,
    source_removal_ablation: dict[str, Any] | None = None,
    semantic_source_removal_ablation: dict[str, Any] | None = None,
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
    paraphrase_p95 = None
    if semantic_paraphrase_ablation is not None:
        paraphrase_p95 = latency_p95(semantic_paraphrase_ablation)
        checks.update(
            summary_checks(
                semantic_paraphrase_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="semantic_paraphrase_",
            )
        )
    semantic_no_exact_p95 = None
    if semantic_no_exact_anchor_ablation is not None:
        semantic_no_exact_p95 = latency_p95(semantic_no_exact_anchor_ablation)
        checks.update(
            summary_checks(
                semantic_no_exact_anchor_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="semantic_no_exact_anchor_",
            )
        )
    negative_control_p95 = None
    if negative_control_ablation is not None:
        negative_control_p95 = latency_p95(negative_control_ablation)
        checks.update(
            summary_checks(
                negative_control_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="negative_control_",
            )
        )
    source_removal_p95 = None
    if source_removal_ablation is not None:
        source_removal_p95 = latency_p95(source_removal_ablation)
        checks.update(
            summary_checks(
                source_removal_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="source_removal_",
            )
        )
    semantic_source_removal_p95 = None
    if semantic_source_removal_ablation is not None:
        semantic_source_removal_p95 = latency_p95(semantic_source_removal_ablation)
        checks.update(
            summary_checks(
                semantic_source_removal_ablation,
                max_mean_latency_ms=max_mean_latency_ms,
                max_p95_latency_ms=max_p95_latency_ms,
                prefix="semantic_source_removal_",
            )
        )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "max_mean_latency_ms": max_mean_latency_ms,
        "max_p95_latency_ms": max_p95_latency_ms,
        "p95_latency_ms": round(float(p95), 3),
        "no_exact_anchor_p95_latency_ms": None if ablation_p95 is None else round(float(ablation_p95), 3),
        "semantic_paraphrase_p95_latency_ms": None if paraphrase_p95 is None else round(float(paraphrase_p95), 3),
        "semantic_no_exact_anchor_p95_latency_ms": None if semantic_no_exact_p95 is None else round(float(semantic_no_exact_p95), 3),
        "negative_control_p95_latency_ms": None if negative_control_p95 is None else round(float(negative_control_p95), 3),
        "source_removal_p95_latency_ms": None if source_removal_p95 is None else round(float(source_removal_p95), 3),
        "semantic_source_removal_p95_latency_ms": None if semantic_source_removal_p95 is None else round(float(semantic_source_removal_p95), 3),
    }


def paraphrased_cases(dataset: Path) -> list[dict[str, Any]]:
    cases = load_cases(dataset)
    out: list[dict[str, Any]] = []
    for case in cases:
        updated = dict(case)
        updated["query"] = SEMANTIC_PARAPHRASES[case["id"]]
        updated["id"] = f"{case['id']}_semantic_paraphrase"
        updated["notes"] = f"Semantic paraphrase of {case['id']}: {case.get('notes', '')}"
        out.append(updated)
    return out


def negative_control_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case_id, query in NEGATIVE_CONTROL_QUERIES.items():
        cases.append(
            {
                "id": case_id,
                "category": "unanswerable",
                "query": query,
                "should_retrieve": False,
                "retrieval_ratio_target": [0.0, 0.01],
                "required_source_ids": [],
                "forbidden_source_ids": [],
                "expected_terms": [],
                "forbidden_terms": [],
                "must_abstain": True,
                "requires_conflict_resolution": False,
                "requires_safety_priority": False,
                "provenance_required": False,
                "max_evidence_items": 0,
                "answer_contract": "abstain",
                "notes": "External near-miss negative control: mentions known products but asks for unsupported current/product facts.",
            }
        )
    return cases


def run_summary(dataset: Path, *, disabled_experts: set[str] | None = None, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    router = MoMEMoCERouter(load_corpus(dataset), candidate_backend="indexed", dataset_path=dataset, disabled_experts=disabled_experts)
    return benchmark(router, cases if cases is not None else load_cases(dataset), validate_artifacts=False)


def source_removal_sensitivity(dataset: Path, *, semantic: bool = False) -> dict[str, Any]:
    started = datetime.now(UTC)
    items = load_corpus(dataset)
    cases = [case for case in (paraphrased_cases(dataset) if semantic else load_cases(dataset)) if case.get("required_source_ids")]
    results: list[dict[str, Any]] = []
    latencies: list[float] = []
    selected_counts: list[int] = []
    for case in cases:
        required = set(case["required_source_ids"])
        router = MoMEMoCERouter([item for item in items if item.id not in required], candidate_backend="indexed", dataset_path=dataset)
        result = router.route(case["query"])
        passed = len(result.selected_ids) == 0 and result.decision == "searched_no_authoritative_evidence"
        latencies.append(float(result.latency_ms))
        selected_counts.append(len(result.selected_ids))
        results.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "removed_source_ids": sorted(required),
                "passed": passed,
                "decision": result.decision,
                "selected_ids": result.selected_ids,
                "latency_ms": round(float(result.latency_ms), 3),
            }
        )
    passed_count = sum(1 for result in results if result["passed"])
    mean_latency = statistics.fmean(latencies) if latencies else 0.0
    p50_latency = statistics.median(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0
    return {
        "schema_version": "mome_moce.source_removal_sensitivity.v0.1",
        "created_at": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "semantic_queries": semantic,
        "cases": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "quality": passed_count / len(results) if results else 0.0,
        "evidence_metrics": {
            "avg_selected": round(statistics.fmean(selected_counts), 4) if selected_counts else 0.0,
            "avg_required": 0.0,
            "required_recall": 1.0,
            "required_only_precision": 1.0 if sum(selected_counts) == 0 else 0.0,
            "forbidden_hits": 0,
        },
        "latency_ms": {"mean": round(mean_latency, 3), "p50": round(p50_latency, 3), "max": round(max_latency, 3)},
        "results": results,
    }


def run_gate(
    dataset: Path,
    *,
    max_mean_latency_ms: float,
    max_p95_latency_ms: float,
    include_no_exact_anchor_ablation: bool = True,
    include_semantic_paraphrase_ablation: bool = True,
    include_semantic_no_exact_anchor_ablation: bool = True,
    include_negative_control_ablation: bool = True,
    include_source_removal_ablation: bool = True,
    include_semantic_source_removal_ablation: bool = True,
) -> dict[str, Any]:
    manifest = write_dataset(dataset)
    summary = run_summary(dataset)
    semantic_cases = paraphrased_cases(dataset)
    no_exact_anchor_ablation = run_summary(dataset, disabled_experts={"exact_anchor_memory"}) if include_no_exact_anchor_ablation else None
    semantic_paraphrase_ablation = run_summary(dataset, cases=semantic_cases) if include_semantic_paraphrase_ablation else None
    semantic_no_exact_anchor_ablation = (
        run_summary(dataset, disabled_experts={"exact_anchor_memory"}, cases=semantic_cases)
        if include_semantic_no_exact_anchor_ablation
        else None
    )
    negative_control_ablation = run_summary(dataset, cases=negative_control_cases()) if include_negative_control_ablation else None
    source_removal_ablation = source_removal_sensitivity(dataset) if include_source_removal_ablation else None
    semantic_source_removal_ablation = source_removal_sensitivity(dataset, semantic=True) if include_semantic_source_removal_ablation else None
    status = gate_status(
        summary,
        max_mean_latency_ms=max_mean_latency_ms,
        max_p95_latency_ms=max_p95_latency_ms,
        no_exact_anchor_ablation=no_exact_anchor_ablation,
        semantic_paraphrase_ablation=semantic_paraphrase_ablation,
        semantic_no_exact_anchor_ablation=semantic_no_exact_anchor_ablation,
        negative_control_ablation=negative_control_ablation,
        source_removal_ablation=source_removal_ablation,
        semantic_source_removal_ablation=semantic_source_removal_ablation,
    )
    return {
        "schema_version": "mome_moce.external_generalization_gate.v0.1",
        "created_at": utc_now(),
        "dataset": str(dataset),
        "dataset_manifest": manifest,
        "summary": summary,
        "no_exact_anchor_ablation": no_exact_anchor_ablation,
        "semantic_paraphrase_ablation": semantic_paraphrase_ablation,
        "semantic_no_exact_anchor_ablation": semantic_no_exact_anchor_ablation,
        "negative_control_ablation": negative_control_ablation,
        "source_removal_ablation": source_removal_ablation,
        "semantic_source_removal_ablation": semantic_source_removal_ablation,
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
    if gate.get("semantic_paraphrase_ablation") is not None:
        paraphrase = gate["semantic_paraphrase_ablation"]
        paraphrase_metrics = paraphrase.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## Semantic Paraphrase Ablation",
                "",
                "This reruns the external cases with hand-paraphrased queries that avoid copying the original question wording. Passing it means the gate is less dependent on exact query phrasing.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{paraphrase['passed']} / {paraphrase['cases']}` |",
                f"| Quality | `{paraphrase['quality']:.4f}` |",
                f"| Required recall | `{paraphrase_metrics.get('required_recall', 0.0):.4f}` |",
                f"| Required-only precision | `{paraphrase_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Forbidden hits | `{paraphrase_metrics.get('forbidden_hits', 0)}` |",
                f"| Mean latency | `{summary_latency(paraphrase, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['semantic_paraphrase_p95_latency_ms']:.3f} ms` |",
            ]
        )
    if gate.get("semantic_no_exact_anchor_ablation") is not None:
        combined = gate["semantic_no_exact_anchor_ablation"]
        combined_metrics = combined.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## Semantic Paraphrase Without Exact Anchor",
                "",
                "This reruns the hand-paraphrased external cases with `exact_anchor_memory` disabled. Passing it means the router can handle the external pack without exact-anchor expert support and without copied query wording.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{combined['passed']} / {combined['cases']}` |",
                f"| Quality | `{combined['quality']:.4f}` |",
                f"| Required recall | `{combined_metrics.get('required_recall', 0.0):.4f}` |",
                f"| Required-only precision | `{combined_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Forbidden hits | `{combined_metrics.get('forbidden_hits', 0)}` |",
                f"| Mean latency | `{summary_latency(combined, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['semantic_no_exact_anchor_p95_latency_ms']:.3f} ms` |",
            ]
        )
    if gate.get("negative_control_ablation") is not None:
        negative = gate["negative_control_ablation"]
        negative_metrics = negative.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## Negative Control Abstention",
                "",
                "This runs near-miss external questions that mention known products but ask for unsupported current facts such as app releases, SLAs, pricing, and certifications. Passing it means the router abstains instead of over-retrieving related identity notes.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{negative['passed']} / {negative['cases']}` |",
                f"| Quality | `{negative['quality']:.4f}` |",
                f"| Required recall | `{negative_metrics.get('required_recall', 0.0):.4f}` |",
                f"| Required-only precision | `{negative_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Forbidden hits | `{negative_metrics.get('forbidden_hits', 0)}` |",
                f"| Avg selected | `{negative_metrics.get('avg_selected', 0.0):.4f}` |",
                f"| Mean latency | `{summary_latency(negative, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['negative_control_p95_latency_ms']:.3f} ms` |",
            ]
        )
    if gate.get("source_removal_ablation") is not None:
        removal = gate["source_removal_ablation"]
        removal_metrics = removal.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## Source-Removal Sensitivity",
                "",
                "This removes each required external source and reruns that case. Passing it means the router abstains instead of selecting adjacent evidence when the necessary source is missing.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{removal['passed']} / {removal['cases']}` |",
                f"| Quality | `{removal['quality']:.4f}` |",
                f"| Required-only precision | `{removal_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Avg selected | `{removal_metrics.get('avg_selected', 0.0):.4f}` |",
                f"| Mean latency | `{summary_latency(removal, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['source_removal_p95_latency_ms']:.3f} ms` |",
            ]
        )
    if gate.get("semantic_source_removal_ablation") is not None:
        removal = gate["semantic_source_removal_ablation"]
        removal_metrics = removal.get("evidence_metrics", {})
        lines.extend(
            [
                "",
                "## Semantic Source-Removal Sensitivity",
                "",
                "This removes each required external source and reruns the hand-paraphrased query. Passing it means required-source causality holds even when the original query wording changes.",
                "",
                "| Metric | Value |",
                "|---|---:|",
                f"| Passed | `{removal['passed']} / {removal['cases']}` |",
                f"| Quality | `{removal['quality']:.4f}` |",
                f"| Required-only precision | `{removal_metrics.get('required_only_precision', 0.0):.4f}` |",
                f"| Avg selected | `{removal_metrics.get('avg_selected', 0.0):.4f}` |",
                f"| Mean latency | `{summary_latency(removal, 'mean'):.3f} ms` |",
                f"| P95 latency | `{status['semantic_source_removal_p95_latency_ms']:.3f} ms` |",
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
    parser.add_argument("--skip-semantic-paraphrase-ablation", action="store_true")
    parser.add_argument("--skip-semantic-no-exact-anchor-ablation", action="store_true")
    parser.add_argument("--skip-negative-control-ablation", action="store_true")
    parser.add_argument("--skip-source-removal-ablation", action="store_true")
    parser.add_argument("--skip-semantic-source-removal-ablation", action="store_true")
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    gate = run_gate(
        dataset,
        max_mean_latency_ms=args.max_mean_latency_ms,
        max_p95_latency_ms=args.max_p95_latency_ms,
        include_no_exact_anchor_ablation=not args.skip_no_exact_anchor_ablation,
        include_semantic_paraphrase_ablation=not args.skip_semantic_paraphrase_ablation,
        include_semantic_no_exact_anchor_ablation=not args.skip_semantic_no_exact_anchor_ablation,
        include_negative_control_ablation=not args.skip_negative_control_ablation,
        include_source_removal_ablation=not args.skip_source_removal_ablation,
        include_semantic_source_removal_ablation=not args.skip_semantic_source_removal_ablation,
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
                    "semantic_paraphrase_passed": None
                    if gate.get("semantic_paraphrase_ablation") is None
                    else gate["semantic_paraphrase_ablation"]["passed"],
                    "semantic_paraphrase_p95_latency_ms": gate["status"]["semantic_paraphrase_p95_latency_ms"],
                    "semantic_no_exact_anchor_passed": None
                    if gate.get("semantic_no_exact_anchor_ablation") is None
                    else gate["semantic_no_exact_anchor_ablation"]["passed"],
                    "semantic_no_exact_anchor_p95_latency_ms": gate["status"]["semantic_no_exact_anchor_p95_latency_ms"],
                    "negative_control_passed": None
                    if gate.get("negative_control_ablation") is None
                    else gate["negative_control_ablation"]["passed"],
                    "negative_control_p95_latency_ms": gate["status"]["negative_control_p95_latency_ms"],
                    "source_removal_passed": None
                    if gate.get("source_removal_ablation") is None
                    else gate["source_removal_ablation"]["passed"],
                    "source_removal_p95_latency_ms": gate["status"]["source_removal_p95_latency_ms"],
                    "semantic_source_removal_passed": None
                    if gate.get("semantic_source_removal_ablation") is None
                    else gate["semantic_source_removal_ablation"]["passed"],
                    "semantic_source_removal_p95_latency_ms": gate["status"]["semantic_source_removal_p95_latency_ms"],
                },
            },
            indent=2,
        )
    )
    return 0 if gate["status"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
