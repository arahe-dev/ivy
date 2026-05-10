from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import (
        MoMEMoCERouter,
        evaluate_case,
        load_cases,
        load_corpus,
        query_has_anchor,
        query_requests_decoy,
        query_requests_latest,
        query_requests_stale_or_comparison,
        requested_families,
        strict_identifiers,
        tokenize,
    )
except ModuleNotFoundError:
    from scripts.mome_moce_harness import (
        MoMEMoCERouter,
        evaluate_case,
        load_cases,
        load_corpus,
        query_has_anchor,
        query_requests_decoy,
        query_requests_latest,
        query_requests_stale_or_comparison,
        requested_families,
        strict_identifiers,
        tokenize,
    )


ROOT = Path(__file__).resolve().parents[1]


def candidate_ids(router: MoMEMoCERouter, query: str) -> list[str]:
    q_tokens = tokenize(query)
    q_token_set = set(q_tokens)
    families = requested_families(query)
    decoy_requested = query_requests_decoy(query)
    stale_requested = query_requests_stale_or_comparison(query)
    latest_requested = query_requests_latest(query)
    strict_terms = strict_identifiers(query)
    if router._generic_no_context_question(query):  # noqa: SLF001 - comparison harness intentionally probes internals.
        families = set()
        decoy_requested = False
        stale_requested = False
        latest_requested = False
        strict_terms = []
    if not (query_has_anchor(query) or families or strict_terms):
        return []
    rows = router._candidate_rows(  # noqa: SLF001
        query=query,
        q_tokens=q_tokens,
        q_token_set=q_token_set,
        families=families,
        decoy_requested=decoy_requested,
        stale_requested=stale_requested,
        latest_requested=latest_requested,
        strict_terms=strict_terms,
    )
    return [item.id for item, _, _ in rows]


def jaccard(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    return len(left_set & right_set) / len(left_set | right_set)


def run_backend(dataset: Path, backend: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    items = load_corpus(dataset)
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)
    candidate_preload_ms = router.rust_index.preload_cases() if router.rust_index is not None else 0.0
    rows = []
    for case in cases:
        candidates = candidate_ids(router, case["query"])
        result = router.route(case["query"])
        evaluated = evaluate_case(case, result)
        required = set(case.get("required_source_ids", []))
        rows.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "candidate_ids": candidates,
                "candidate_count": len(candidates),
                "candidate_required_misses": sorted(required - set(candidates)),
                "selected_ids": result.selected_ids,
                "passed": evaluated["passed"],
                "latency_ms": evaluated["latency_ms"],
            }
        )
    required_total = sum(len(case.get("required_source_ids", [])) for case in cases)
    candidate_hits = sum(
        len(set(case.get("required_source_ids", [])) & set(row["candidate_ids"]))
        for case, row in zip(cases, rows, strict=True)
    )
    passed = sum(1 for row in rows if row["passed"])
    return {
        "backend": backend,
        "cases": len(cases),
        "passed": passed,
        "quality": round(passed / len(cases), 6) if cases else 0.0,
        "candidate_required_recall": round(candidate_hits / required_total, 6) if required_total else 1.0,
        "candidate_preload_ms": round(candidate_preload_ms, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(row["latency_ms"] for row in rows), 3) if rows else 0.0,
            "p50": round(statistics.median(row["latency_ms"] for row in rows), 3) if rows else 0.0,
            "max": round(max(row["latency_ms"] for row in rows), 3) if rows else 0.0,
        },
        "rows": rows,
    }


def compare_backends(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for left, right in zip(reference["rows"], candidate["rows"], strict=True):
        value = jaccard(left["candidate_ids"], right["candidate_ids"])
        rows.append(
            {
                "case_id": left["case_id"],
                "category": left["category"],
                "candidate_jaccard": round(value, 6),
                "selected_match": left["selected_ids"] == right["selected_ids"],
                "reference_only_candidates": sorted(set(left["candidate_ids"]) - set(right["candidate_ids"])),
                "candidate_only_candidates": sorted(set(right["candidate_ids"]) - set(left["candidate_ids"])),
                "reference_selected_ids": left["selected_ids"],
                "candidate_selected_ids": right["selected_ids"],
            }
        )
    return {
        "reference_backend": reference["backend"],
        "candidate_backend": candidate["backend"],
        "candidate_jaccard_mean": round(statistics.fmean(row["candidate_jaccard"] for row in rows), 6) if rows else 1.0,
        "candidate_jaccard_min": min((row["candidate_jaccard"] for row in rows), default=1.0),
        "selected_exact_match_rate": round(sum(1 for row in rows if row["selected_match"]) / len(rows), 6) if rows else 1.0,
        "rows_below_0_98": [row for row in rows if row["candidate_jaccard"] < 0.98],
        "rows": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    backend_rows = [
        "| backend | quality | passed | candidate required recall | preload ms | mean ms | p50 ms | max ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for backend in payload["backends"].values():
        backend_rows.append(
            f"| {backend['backend']} | {backend['quality']:.3f} | {backend['passed']}/{backend['cases']} | "
            f"{backend['candidate_required_recall']:.3f} | {backend['candidate_preload_ms']:.3f} | {backend['latency_ms']['mean']:.3f} | "
            f"{backend['latency_ms']['p50']:.3f} | {backend['latency_ms']['max']:.3f} |"
        )
    comparison_rows = [
        "| comparison | candidate Jaccard mean | candidate Jaccard min | selected match rate | rows < 0.98 |",
        "|---|---:|---:|---:|---:|",
    ]
    for comparison in payload["comparisons"]:
        comparison_rows.append(
            f"| {comparison['reference_backend']} -> {comparison['candidate_backend']} | "
            f"{comparison['candidate_jaccard_mean']:.3f} | {comparison['candidate_jaccard_min']:.3f} | "
            f"{comparison['selected_exact_match_rate']:.3f} | {len(comparison['rows_below_0_98'])} |"
        )
    return "\n".join(
        [
            "# Candidate Backend Comparison",
            "",
            f"Dataset: `{payload['dataset']}`",
            f"Cases: {payload['cases']}",
            "",
            *backend_rows,
            "",
            *comparison_rows,
            "",
            "Candidate parity compares the Python pre-scored candidate IDs emitted before final policy selection.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare scan/indexed/rust candidate backends on one labeled dataset.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real")
    parser.add_argument("--backends", nargs="+", choices=["scan", "indexed", "rust"], default=["indexed", "rust"])
    parser.add_argument("--reference", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases = load_cases(dataset)
    if args.limit:
        cases = cases[: args.limit]
    backends = list(dict.fromkeys([args.reference, *args.backends]))
    results = {backend: run_backend(dataset, backend, cases) for backend in backends}
    comparisons = [
        compare_backends(results[args.reference], results[backend])
        for backend in backends
        if backend != args.reference
    ]
    payload = {
        "runner_version": "candidate_backend_comparison.v0.1",
        "dataset": str(dataset),
        "cases": len(cases),
        "reference": args.reference,
        "backends": results,
        "comparisons": comparisons,
    }
    output_json = args.output_json or ROOT / "out" / f"candidate_backend_comparison_{dataset.name}.json"
    output_md = args.output_md or ROOT / "out" / f"candidate_backend_comparison_{dataset.name}.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(markdown(payload), encoding="utf-8")
    printable = {
        "output_json": str(output_json),
        "output_md": str(output_md),
        "comparisons": [
            {
                key: value
                for key, value in comparison.items()
                if key in {"reference_backend", "candidate_backend", "candidate_jaccard_mean", "candidate_jaccard_min", "selected_exact_match_rate"}
            }
            for comparison in comparisons
        ],
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if all(result["quality"] == 1.0 for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
