from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from run_external_generalization_gate import run_gate as run_external_generalization_gate
    from run_context_memory_plugin_benchmark import run_benchmark
    from run_mined_case_policy_eval import evaluate, load_cases
    from run_reranker_feature_eval import baseline_result, promote_winner_policy, run_feature_eval
except ModuleNotFoundError:
    from scripts.run_external_generalization_gate import run_gate as run_external_generalization_gate
    from scripts.run_context_memory_plugin_benchmark import run_benchmark
    from scripts.run_mined_case_policy_eval import evaluate, load_cases
    from scripts.run_reranker_feature_eval import baseline_result, promote_winner_policy, run_feature_eval


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "out" / "autoresearch_loop" / "memory_store"
DEFAULT_PLUGIN_STORE = ROOT / "out" / "regression_gate_plugin_store"
DEFAULT_CASES = ROOT / "docs" / "AUTORESEARCH_MINED_EVAL_CASES.json"
DEFAULT_OUT = ROOT / "docs" / "AUTORESEARCH_REGRESSION_GATE.md"
DEFAULT_EXTERNAL_DATASET = ROOT / "out" / "context_stress_external_signal_recall"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def rank_policy_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results, key=lambda row: (row["passed"], -row["avg_router_latency_ms"], -row["avg_wall_ms"]), reverse=True)


def gate_status(
    gate: dict[str, Any],
    *,
    max_router_ms: float,
    max_plugin_router_ms: float | None = None,
    max_wall_ms: float = 35.0,
    max_plugin_wall_ms: float = 25.0,
) -> dict[str, Any]:
    max_plugin_router_ms = max_router_ms if max_plugin_router_ms is None else max_plugin_router_ms
    mined = gate["mined_policy"]["winner"]
    feature = gate["feature_eval"]["winner"]
    plugin = gate["plugin_benchmark"]["summary"]
    checks = {
        "mined_policy_all_pass": mined["passed"] == mined["total"],
        "feature_eval_all_pass": feature["passed"] == feature["total"],
        "plugin_benchmark_all_pass": plugin["passed_expectations"] == plugin["query_count"],
        "feature_router_under_budget": float(feature["avg_router_latency_ms"]) <= max_router_ms,
        "plugin_router_under_budget": float(plugin["avg_router_latency_ms"]) <= max_plugin_router_ms,
        "mined_policy_wall_under_budget": float(mined["avg_wall_ms"]) <= max_wall_ms,
        "feature_wall_under_budget": float(feature["avg_wall_ms"]) <= max_wall_ms,
        "plugin_wall_under_budget": float(plugin["avg_query_wall_ms"]) <= max_plugin_wall_ms,
    }
    if "external_generalization" in gate:
        external = gate["external_generalization"]
        external_summary = external["summary"]
        external_metrics = external_summary["evidence_metrics"]
        checks.update(
            {
                "external_generalization_all_pass": external["status"]["passed"],
                "external_generalization_required_recall": float(external_metrics["required_recall"]) == 1.0,
                "external_generalization_required_precision": float(external_metrics["required_only_precision"]) == 1.0,
                "external_generalization_no_forbidden_hits": int(external_metrics["forbidden_hits"]) == 0,
            }
        )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "max_router_ms": max_router_ms,
        "max_plugin_router_ms": max_plugin_router_ms,
        "max_wall_ms": max_wall_ms,
        "max_plugin_wall_ms": max_plugin_wall_ms,
    }


def run_gate(
    *,
    store: Path,
    plugin_store: Path,
    cases_path: Path,
    source_root: Path,
    candidates: list[int],
    max_router_ms: float,
    max_plugin_router_ms: float,
    max_wall_ms: float,
    max_plugin_wall_ms: float,
    promote: bool,
    include_external_generalization: bool = True,
    external_dataset: Path = DEFAULT_EXTERNAL_DATASET,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    mined_results = [evaluate(store, cases, max_prefilter_items=value) for value in candidates]
    mined_ranked = rank_policy_results(mined_results)
    feature_ranked, feature_winner = run_feature_eval(store, cases_path, max_prefilter_items=int(mined_ranked[0]["max_prefilter_items"]))
    promotion = promote_winner_policy(store, feature_winner, baseline_result(feature_ranked)) if promote else {"promoted": False, "reason": "promotion disabled"}
    plugin_result = run_benchmark(plugin_store, source_root=source_root, reset=True)
    gate = {
        "schema_version": "ivy_context_memory.regression_gate.v0.1",
        "created_at": utc_now(),
        "store": str(store),
        "cases": str(cases_path),
        "mined_policy": {"results": mined_ranked, "winner": mined_ranked[0]},
        "feature_eval": {"results": feature_ranked, "winner": feature_winner, "promotion": promotion},
        "plugin_benchmark": plugin_result,
    }
    if include_external_generalization:
        gate["external_generalization"] = run_external_generalization_gate(
            external_dataset,
            max_mean_latency_ms=2.0,
            max_p95_latency_ms=5.0,
        )
    gate["status"] = gate_status(
        gate,
        max_router_ms=max_router_ms,
        max_plugin_router_ms=max_plugin_router_ms,
        max_wall_ms=max_wall_ms,
        max_plugin_wall_ms=max_plugin_wall_ms,
    )
    return gate


def write_gate_report(gate: dict[str, Any], out: Path) -> None:
    status = gate["status"]
    mined = gate["mined_policy"]["winner"]
    feature = gate["feature_eval"]["winner"]
    plugin = gate["plugin_benchmark"]["summary"]
    lines = [
        "# Autoresearch Context Memory Regression Gate",
        "",
        f"Created: `{gate['created_at']}`",
        f"Gate passed: `{status['passed']}`",
        f"Mined/feature router budget: `{status['max_router_ms']} ms`",
        f"Full plugin router budget: `{status['max_plugin_router_ms']} ms`",
        f"Mined/feature wall budget: `{status['max_wall_ms']} ms`",
        f"Full plugin wall budget: `{status['max_plugin_wall_ms']} ms`",
        "",
        "## Summary",
        "",
        "| Gate | Result |",
        "|---|---:|",
        f"| Mined policy winner | `max_prefilter_items={mined['max_prefilter_items']}` |",
        f"| Mined policy pass | `{mined['passed']} / {mined['total']}` |",
        f"| Mined policy avg wall | `{mined['avg_wall_ms']} ms` |",
        f"| Feature profile winner | `{feature['feature_profile']}` |",
        f"| Feature pass | `{feature['passed']} / {feature['total']}` |",
        f"| Feature avg wall | `{feature['avg_wall_ms']} ms` |",
        f"| Feature avg router | `{feature['avg_router_latency_ms']} ms` |",
        f"| Plugin benchmark pass | `{plugin['passed_expectations']} / {plugin['query_count']}` |",
        f"| Plugin avg query wall | `{plugin['avg_query_wall_ms']} ms` |",
        f"| Plugin avg router | `{plugin['avg_router_latency_ms']} ms` |",
        f"| Promotion | `{gate['feature_eval']['promotion'].get('promoted')}` |",
    ]
    if "external_generalization" in gate:
        external = gate["external_generalization"]
        external_summary = external["summary"]
        external_metrics = external_summary["evidence_metrics"]
        external_latency = external_summary.get("latency_ms", {})
        lines.extend(
            [
                f"| External generalization pass | `{external_summary['passed']} / {external_summary['cases']}` |",
                f"| External required precision | `{external_metrics['required_only_precision']}` |",
                f"| External forbidden hits | `{external_metrics['forbidden_hits']}` |",
                f"| External mean latency | `{external_latency.get('mean')} ms` |",
                f"| External p95 latency | `{external['status']['p95_latency_ms']} ms` |",
            ]
        )
        if external.get("no_exact_anchor_ablation") is not None:
            ablation = external["no_exact_anchor_ablation"]
            ablation_latency = ablation.get("latency_ms", {})
            lines.extend(
                [
                    f"| External no-exact-anchor pass | `{ablation['passed']} / {ablation['cases']}` |",
                    f"| External no-exact-anchor mean latency | `{ablation_latency.get('mean')} ms` |",
                    f"| External no-exact-anchor p95 latency | `{external['status']['no_exact_anchor_p95_latency_ms']} ms` |",
                ]
            )
        if external.get("semantic_paraphrase_ablation") is not None:
            paraphrase = external["semantic_paraphrase_ablation"]
            paraphrase_latency = paraphrase.get("latency_ms", {})
            lines.extend(
                [
                    f"| External semantic-paraphrase pass | `{paraphrase['passed']} / {paraphrase['cases']}` |",
                    f"| External semantic-paraphrase mean latency | `{paraphrase_latency.get('mean')} ms` |",
                    f"| External semantic-paraphrase p95 latency | `{external['status']['semantic_paraphrase_p95_latency_ms']} ms` |",
                ]
            )
    lines.extend(["", "## Checks", "", "| Check | Pass |", "|---|---:|"])
    for name, passed in status["checks"].items():
        lines.append(f"| `{name}` | `{passed}` |")
    lines.extend(["", "## Feature Profiles", "", "| Profile | Passed | Avg wall ms | Avg router ms |", "|---|---:|---:|---:|"])
    for row in gate["feature_eval"]["results"]:
        lines.append(f"| {row['feature_profile']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
    lines.extend(["", "## Mined Policy Candidates", "", "| max_prefilter_items | Passed | Avg wall ms | Avg router ms |", "|---:|---:|---:|---:|"])
    for row in gate["mined_policy"]["results"]:
        lines.append(f"| {row['max_prefilter_items']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
    if "external_generalization" in gate:
        lines.extend(["", "## External Generalization", "", "| Case | Pass | Selected | Latency ms |", "|---|---:|---|---:|"])
        for result in gate["external_generalization"]["summary"]["results"]:
            selected = ", ".join(result.get("selected_ids", []))
            lines.append(f"| `{result['case_id']}` | `{result['passed']}` | `{selected}` | `{result.get('latency_ms', 0.0)}` |")
        if gate["external_generalization"].get("no_exact_anchor_ablation") is not None:
            lines.extend(["", "## External No-Exact-Anchor Ablation", "", "| Case | Pass | Selected | Latency ms |", "|---|---:|---|---:|"])
            for result in gate["external_generalization"]["no_exact_anchor_ablation"]["results"]:
                selected = ", ".join(result.get("selected_ids", []))
                lines.append(f"| `{result['case_id']}` | `{result['passed']}` | `{selected}` | `{result.get('latency_ms', 0.0)}` |")
        if gate["external_generalization"].get("semantic_paraphrase_ablation") is not None:
            lines.extend(["", "## External Semantic Paraphrase Ablation", "", "| Case | Pass | Selected | Latency ms |", "|---|---:|---|---:|"])
            for result in gate["external_generalization"]["semantic_paraphrase_ablation"]["results"]:
                selected = ", ".join(result.get("selected_ids", []))
                lines.append(f"| `{result['case_id']}` | `{result['passed']}` | `{selected}` | `{result.get('latency_ms', 0.0)}` |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IVY context-memory regression gate.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--plugin-store", type=Path, default=DEFAULT_PLUGIN_STORE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--candidate", type=int, action="append", default=[16, 32, 64, 128])
    parser.add_argument("--max-router-ms", type=float, default=5.0)
    parser.add_argument("--max-plugin-router-ms", type=float, default=15.0)
    parser.add_argument("--max-wall-ms", type=float, default=35.0)
    parser.add_argument("--max-plugin-wall-ms", type=float, default=25.0)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--skip-external-generalization", action="store_true")
    parser.add_argument("--external-dataset", type=Path, default=DEFAULT_EXTERNAL_DATASET)
    args = parser.parse_args()

    gate = run_gate(
        store=args.store.resolve(),
        plugin_store=args.plugin_store.resolve(),
        cases_path=args.cases.resolve(),
        source_root=args.source_root.resolve(),
        candidates=args.candidate,
        max_router_ms=args.max_router_ms,
        max_plugin_router_ms=args.max_plugin_router_ms,
        max_wall_ms=args.max_wall_ms,
        max_plugin_wall_ms=args.max_plugin_wall_ms,
        promote=args.promote,
        include_external_generalization=not args.skip_external_generalization,
        external_dataset=args.external_dataset.resolve(),
    )
    write_gate_report(gate, args.out.resolve())
    print(json.dumps({"ok": True, "passed": gate["status"]["passed"], "report": str(args.out), "status": gate["status"]}, indent=2))
    return 0 if gate["status"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
