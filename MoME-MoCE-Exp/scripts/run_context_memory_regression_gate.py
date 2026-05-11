from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from run_context_memory_plugin_benchmark import run_benchmark
    from run_mined_case_policy_eval import evaluate, load_cases
    from run_reranker_feature_eval import baseline_result, promote_winner_policy, run_feature_eval
except ModuleNotFoundError:
    from scripts.run_context_memory_plugin_benchmark import run_benchmark
    from scripts.run_mined_case_policy_eval import evaluate, load_cases
    from scripts.run_reranker_feature_eval import baseline_result, promote_winner_policy, run_feature_eval


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / "out" / "autoresearch_loop" / "memory_store"
DEFAULT_PLUGIN_STORE = ROOT / "out" / "regression_gate_plugin_store"
DEFAULT_CASES = ROOT / "docs" / "AUTORESEARCH_MINED_EVAL_CASES.json"
DEFAULT_OUT = ROOT / "docs" / "AUTORESEARCH_REGRESSION_GATE.md"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def rank_policy_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results, key=lambda row: (row["passed"], -row["avg_router_latency_ms"], -row["avg_wall_ms"]), reverse=True)


def gate_status(gate: dict[str, Any], *, max_router_ms: float, max_plugin_router_ms: float | None = None) -> dict[str, Any]:
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
    }
    return {"passed": all(checks.values()), "checks": checks, "max_router_ms": max_router_ms, "max_plugin_router_ms": max_plugin_router_ms}


def run_gate(
    *,
    store: Path,
    plugin_store: Path,
    cases_path: Path,
    source_root: Path,
    candidates: list[int],
    max_router_ms: float,
    max_plugin_router_ms: float,
    promote: bool,
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
    gate["status"] = gate_status(gate, max_router_ms=max_router_ms, max_plugin_router_ms=max_plugin_router_ms)
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
        "",
        "## Summary",
        "",
        "| Gate | Result |",
        "|---|---:|",
        f"| Mined policy winner | `max_prefilter_items={mined['max_prefilter_items']}` |",
        f"| Mined policy pass | `{mined['passed']} / {mined['total']}` |",
        f"| Feature profile winner | `{feature['feature_profile']}` |",
        f"| Feature pass | `{feature['passed']} / {feature['total']}` |",
        f"| Feature avg router | `{feature['avg_router_latency_ms']} ms` |",
        f"| Plugin benchmark pass | `{plugin['passed_expectations']} / {plugin['query_count']}` |",
        f"| Plugin avg router | `{plugin['avg_router_latency_ms']} ms` |",
        f"| Promotion | `{gate['feature_eval']['promotion'].get('promoted')}` |",
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for name, passed in status["checks"].items():
        lines.append(f"| `{name}` | `{passed}` |")
    lines.extend(["", "## Feature Profiles", "", "| Profile | Passed | Avg wall ms | Avg router ms |", "|---|---:|---:|---:|"])
    for row in gate["feature_eval"]["results"]:
        lines.append(f"| {row['feature_profile']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
    lines.extend(["", "## Mined Policy Candidates", "", "| max_prefilter_items | Passed | Avg wall ms | Avg router ms |", "|---:|---:|---:|---:|"])
    for row in gate["mined_policy"]["results"]:
        lines.append(f"| {row['max_prefilter_items']} | {row['passed']} / {row['total']} | {row['avg_wall_ms']} | {row['avg_router_latency_ms']} |")
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
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()

    gate = run_gate(
        store=args.store.resolve(),
        plugin_store=args.plugin_store.resolve(),
        cases_path=args.cases.resolve(),
        source_root=args.source_root.resolve(),
        candidates=args.candidate,
        max_router_ms=args.max_router_ms,
        max_plugin_router_ms=args.max_plugin_router_ms,
        promote=args.promote,
    )
    write_gate_report(gate, args.out.resolve())
    print(json.dumps({"ok": True, "passed": gate["status"]["passed"], "report": str(args.out), "status": gate["status"]}, indent=2))
    return 0 if gate["status"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
