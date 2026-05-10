from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

try:
    from mome_moce_harness import (
        CorpusItem,
        MoMEMoCERouter,
        compute_idf,
        default_max_evidence_items,
        load_cases,
        load_corpus,
        norm,
        requested_families,
        strict_identifiers,
        tokenize,
    )
except ModuleNotFoundError:
    from scripts.mome_moce_harness import (
        CorpusItem,
        MoMEMoCERouter,
        compute_idf,
        default_max_evidence_items,
        load_cases,
        load_corpus,
        norm,
        requested_families,
        strict_identifiers,
        tokenize,
    )


ROOT = Path(__file__).resolve().parents[1]


def bm25_score(item: CorpusItem, q_tokens: list[str], idf: dict[str, float], avg_len: float) -> float:
    if not q_tokens:
        return 0.0
    score = 0.0
    k1 = 1.25
    b = 0.72
    dl = max(1, len(item.tokens))
    for token in set(q_tokens):
        tf = item.token_counts.get(token, 0)
        if not tf:
            continue
        denom = tf + k1 * (1 - b + b * dl / max(1, avg_len))
        score += idf.get(token, 0.0) * (tf * (k1 + 1)) / denom
    return score


def top_bm25(items: list[CorpusItem], query: str, *, top_k: int, family_filter: set[str] | None = None) -> list[str]:
    q_tokens = tokenize(query)
    idf = compute_idf(items)
    avg_len = statistics.fmean([len(item.tokens) for item in items]) if items else 1.0
    pool = [item for item in items if not family_filter or item.source_family in family_filter]
    scored = [(item, bm25_score(item, q_tokens, idf, avg_len)) for item in pool]
    scored = [(item, score) for item, score in scored if score > 0]
    scored.sort(key=lambda row: row[1], reverse=True)
    return [item.id for item, _ in scored[:top_k]]


def exact_anchor_only(items: list[CorpusItem], query: str, *, top_k: int) -> list[str]:
    terms = strict_identifiers(query)
    if not terms:
        return []
    q_tokens = tokenize(query)
    idf = compute_idf(items)
    avg_len = statistics.fmean([len(item.tokens) for item in items]) if items else 1.0
    rows = []
    for item in items:
        haystack = norm(item.search_text)
        if any(term in haystack for term in terms):
            rows.append((item, bm25_score(item, q_tokens, idf, avg_len)))
    rows.sort(key=lambda row: row[1], reverse=True)
    return [item.id for item, _ in rows[:top_k]]


def evaluate_selection(
    case: dict[str, Any],
    selected_ids: list[str],
    item_by_id: dict[str, CorpusItem],
    *,
    latency_ms: float,
) -> dict[str, Any]:
    selected = set(selected_ids)
    required = set(case.get("required_source_ids", []))
    forbidden = set(case.get("forbidden_source_ids", []))
    required_hits = sorted(required & selected)
    hit_forbidden = sorted(forbidden & selected)
    missing_required = sorted(required - selected)
    max_evidence_items = int(case.get("max_evidence_items", default_max_evidence_items(case)))
    compactness_pass = len(selected) <= max_evidence_items
    if not case.get("should_retrieve", False):
        passed = not selected
    elif case.get("must_abstain", False):
        passed = not selected
    elif required:
        passed = not missing_required and not hit_forbidden
    else:
        passed = not hit_forbidden and not selected
    passed = bool(passed and compactness_pass)
    selected_items = [item_by_id[item_id] for item_id in selected_ids if item_id in item_by_id]
    stale_bad = [
        item.id
        for item in selected_items
        if item.staleness == "stale" and item.id not in required and item.id not in forbidden
    ]
    decoy_bad = [
        item.id
        for item in selected_items
        if item.authority == "decoy" and item.id not in required and item.id not in forbidden
    ]
    return {
        "case_id": case["id"],
        "category": case["category"],
        "passed": passed,
        "selected_ids": selected_ids,
        "required_source_ids": sorted(required),
        "forbidden_source_ids": sorted(forbidden),
        "missing_required": missing_required,
        "hit_forbidden": hit_forbidden,
        "required_hits": required_hits,
        "extra_selected": sorted(selected - required),
        "max_evidence_items": max_evidence_items,
        "compactness_pass": compactness_pass,
        "latency_ms": round(latency_ms, 3),
        "stale_unrequired": stale_bad,
        "decoy_unrequired": decoy_bad,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for result in results if result["passed"])
    selected_total = sum(len(result["selected_ids"]) for result in results)
    required_total = sum(len(result["required_source_ids"]) for result in results)
    required_hits_total = sum(len(result["required_hits"]) for result in results)
    latencies = [result["latency_ms"] for result in results]
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
        "compactness_pass_rate": round(sum(1 for result in results if result["compactness_pass"]) / len(results), 4)
        if results
        else 0.0,
        "forbidden_hits": sum(len(result["hit_forbidden"]) for result in results),
        "unrequired_stale_hits": sum(len(result["stale_unrequired"]) for result in results),
        "unrequired_decoy_hits": sum(len(result["decoy_unrequired"]) for result in results),
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


def run_baselines(items: list[CorpusItem], cases: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    item_by_id = {item.id: item for item in items}
    router = MoMEMoCERouter(items, top_k=top_k)

    def run_selector(name: str, selector: Callable[[dict[str, Any]], list[str]]) -> dict[str, Any]:
        results = []
        for case in cases:
            start = time.perf_counter()
            selected_ids = selector(case)
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(evaluate_selection(case, selected_ids, item_by_id, latency_ms=latency_ms))
        summary = summarize(results)
        summary["results"] = results
        return summary

    return {
        "naive_bm25_top_k": run_selector(
            "naive_bm25_top_k",
            lambda case: top_bm25(items, case["query"], top_k=top_k),
        ),
        "source_family_bm25_top_k": run_selector(
            "source_family_bm25_top_k",
            lambda case: top_bm25(items, case["query"], top_k=top_k, family_filter=requested_families(case["query"])),
        ),
        "exact_anchor_only": run_selector(
            "exact_anchor_only",
            lambda case: exact_anchor_only(items, case["query"], top_k=top_k),
        ),
        "compact_acca": run_selector(
            "compact_acca",
            lambda case: router.route(case["query"]).selected_ids,
        ),
    }


def markdown_table(payload: dict[str, Any]) -> str:
    rows = [
        "| mode | quality | passed | avg selected | recall | precision | compact pass | forbidden | stale extra | decoy extra | mean ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, summary in payload["modes"].items():
        rows.append(
            "| {name} | {quality:.3f} | {passed}/{cases} | {avg:.3f} | {recall:.3f} | {precision:.3f} | {compact:.3f} | {forbidden} | {stale} | {decoy} | {latency:.3f} |".format(
                name=name,
                quality=summary["quality"],
                passed=summary["passed"],
                cases=summary["cases"],
                avg=summary["avg_selected"],
                recall=summary["required_recall"],
                precision=summary["required_only_precision"],
                compact=summary["compactness_pass_rate"],
                forbidden=summary["forbidden_hits"],
                stale=summary["unrequired_stale_hits"],
                decoy=summary["unrequired_decoy_hits"],
                latency=summary["latency_ms_mean"],
            )
        )
    return "\n".join(
        [
            "# CP5 Baseline Comparison",
            "",
            f"Dataset: `{payload['dataset']}`",
            f"Cases: {payload['cases']}",
            f"Top-k for non-ACCA baselines: {payload['top_k']}",
            "",
            *rows,
            "",
            "Compact ACCA uses the same top-k ceiling but applies the CP4 evidence budget before emitting a packet.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare compact ACCA routing against simple retrieval baselines.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_smoke")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases = load_cases(dataset)
    if args.limit:
        cases = cases[: args.limit]
    items = load_corpus(dataset)
    modes = run_baselines(items, cases, top_k=args.top_k)
    payload = {
        "runner_version": "cp5.baseline_comparison.v0.1",
        "dataset": str(dataset),
        "cases": len(cases),
        "top_k": args.top_k,
        "modes": modes,
    }

    output_json = args.output_json or ROOT / "out" / f"baseline_comparison_{dataset.name}.json"
    output_md = args.output_md or ROOT / "out" / f"baseline_comparison_{dataset.name}.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(markdown_table(payload), encoding="utf-8")

    compact = modes["compact_acca"]
    printable = {
        name: {key: summary[key] for key in ["cases", "passed", "failed", "quality", "avg_selected", "required_recall", "required_only_precision", "forbidden_hits"]}
        for name, summary in modes.items()
    }
    print(json.dumps({"output_json": str(output_json), "output_md": str(output_md), "modes": printable}, ensure_ascii=False, indent=2))
    return 0 if compact["quality"] == 1.0 and compact["required_only_precision"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
