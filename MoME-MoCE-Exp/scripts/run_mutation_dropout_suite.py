from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, evaluate_case, load_cases, load_corpus
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, evaluate_case, load_cases, load_corpus


ROOT = Path(__file__).resolve().parents[1]


DROPOUTS: dict[str, set[str]] = {
    "baseline_compact_acca": set(),
    "drop_exact_anchor_memory": {"exact_anchor_memory"},
    "drop_conflict_graph_memory": {"conflict_graph_memory"},
    "drop_freshness_gate": {"freshness_gate"},
    "drop_safety_gate": {"safety_gate"},
}


def mutate_query(query: str) -> str:
    replacements = [
        ("ctx=8192", "ctx 8192"),
        ("ctx=512", "ctx 512"),
        ("latest", "current"),
        ("current", "latest"),
        ("decoy", "false packet"),
        ("stale", "superseded"),
        ("old", "superseded"),
        ("JSON", "json"),
        ("tool sequence", "tool path"),
        ("Which", "What"),
        ("What", "Which"),
    ]
    mutated = query
    for old, new in replacements:
        if old in mutated:
            mutated = mutated.replace(old, new, 1)
            break
    if mutated == query:
        mutated = f"{query} Cite only the relevant evidence."
    return mutated


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for result in results if result["passed"])
    latencies = [result["latency_ms"] for result in results]
    selected_total = sum(len(result["selected_ids"]) for result in results)
    required_total = sum(len(result["required_source_ids"]) for result in results)
    required_hits_total = sum(len(result["required_hits"]) for result in results)
    by_category: dict[str, list[bool]] = defaultdict(list)
    for result in results:
        by_category[result["category"]].append(bool(result["passed"]))
    return {
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "quality": round(passed / len(results), 6) if results else 0.0,
        "avg_selected": round(selected_total / len(results), 4) if results else 0.0,
        "required_recall": round(required_hits_total / required_total, 4) if required_total else 1.0,
        "required_only_precision": round(required_hits_total / selected_total, 4) if selected_total else 1.0,
        "latency_ms_mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "by_category": {
            category: {
                "cases": len(values),
                "passed": sum(1 for value in values if value),
                "quality": round(sum(1 for value in values if value) / len(values), 6),
            }
            for category, values in sorted(by_category.items())
        },
        "failures": [result for result in results if not result["passed"]],
    }


def run_router_cases(
    cases: list[dict[str, Any]],
    router: MoMEMoCERouter,
    *,
    mutate: bool = False,
) -> dict[str, Any]:
    results = []
    for case in cases:
        routed_case = dict(case)
        if mutate:
            routed_case["original_query"] = case["query"]
            routed_case["query"] = mutate_query(case["query"])
        result = router.route(routed_case["query"])
        evaluated = evaluate_case(routed_case, result)
        if mutate:
            evaluated["original_query"] = case["query"]
        results.append(evaluated)
    summary = summarize(results)
    summary["results"] = results
    return summary


def markdown_report(payload: dict[str, Any]) -> str:
    rows = [
        "| suite | quality | passed | avg selected | recall | precision | mean ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, summary in payload["suites"].items():
        rows.append(
            "| {name} | {quality:.3f} | {passed}/{cases} | {avg:.3f} | {recall:.3f} | {precision:.3f} | {latency:.3f} |".format(
                name=name,
                quality=summary["quality"],
                passed=summary["passed"],
                cases=summary["cases"],
                avg=summary["avg_selected"],
                recall=summary["required_recall"],
                precision=summary["required_only_precision"],
                latency=summary["latency_ms_mean"],
            )
        )
    degradation_rows = [
        "| dropout | quality delta vs baseline | failed cases |",
        "|---|---:|---:|",
    ]
    baseline_quality = payload["suites"]["baseline_compact_acca"]["quality"]
    for name in DROPOUTS:
        if name == "baseline_compact_acca":
            continue
        summary = payload["suites"][name]
        degradation_rows.append(f"| {name} | {summary['quality'] - baseline_quality:.3f} | {summary['failed']} |")
    return "\n".join(
        [
            "# CP6 Mutation And Dropout Suite",
            "",
            f"Dataset: `{payload['dataset']}`",
            f"Cases: {payload['cases']}",
            "",
            *rows,
            "",
            "## Expert Dropout Deltas",
            "",
            *degradation_rows,
            "",
            "Mutation queries are evaluated against the original case labels after a small semantics-preserving rewrite.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CP6 mutation and expert-dropout checks for ACCA routing.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_smoke")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases = load_cases(dataset)
    if args.limit:
        cases = cases[: args.limit]
    items = load_corpus(dataset)

    suites: dict[str, Any] = {}
    for name, disabled in DROPOUTS.items():
        router = MoMEMoCERouter(items, top_k=args.top_k, candidate_k=args.candidate_k, disabled_experts=disabled)
        suites[name] = run_router_cases(cases, router)

    mutation_router = MoMEMoCERouter(items, top_k=args.top_k, candidate_k=args.candidate_k)
    suites["mutated_queries_compact_acca"] = run_router_cases(cases, mutation_router, mutate=True)

    payload = {
        "runner_version": "cp6.mutation_dropout.v0.1",
        "dataset": str(dataset),
        "cases": len(cases),
        "top_k": args.top_k,
        "candidate_k": args.candidate_k,
        "suites": suites,
    }
    output_json = args.output_json or ROOT / "out" / f"mutation_dropout_{dataset.name}.json"
    output_md = args.output_md or ROOT / "out" / f"mutation_dropout_{dataset.name}.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(markdown_report(payload), encoding="utf-8")

    printable = {
        name: {key: summary[key] for key in ["cases", "passed", "failed", "quality", "avg_selected", "required_recall", "required_only_precision"]}
        for name, summary in suites.items()
    }
    print(json.dumps({"output_json": str(output_json), "output_md": str(output_md), "suites": printable}, ensure_ascii=False, indent=2))
    baseline = suites["baseline_compact_acca"]
    mutated = suites["mutated_queries_compact_acca"]
    dropout_degraded = any(suites[name]["quality"] < baseline["quality"] for name in DROPOUTS if name != "baseline_compact_acca")
    return 0 if baseline["quality"] == 1.0 and mutated["quality"] >= 0.9 and dropout_degraded else 1


if __name__ == "__main__":
    raise SystemExit(main())
