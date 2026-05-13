from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from run_librarian_advisor_harness import (
        LibrarianAdvice,
        build_advice,
        read_cases,
        resolve_path,
        route_librarian_bundle,
        route_once,
        router_for_dataset,
        score_selection,
        write_json,
        write_text,
    )
    from mome_moce_harness import MoMEMoCERouter, tokenize
except ModuleNotFoundError:
    from scripts.run_librarian_advisor_harness import (
        LibrarianAdvice,
        build_advice,
        read_cases,
        resolve_path,
        route_librarian_bundle,
        route_once,
        router_for_dataset,
        score_selection,
        write_json,
        write_text,
    )
    from scripts.mome_moce_harness import MoMEMoCERouter, tokenize


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "out" / "blackbox_packet_eval" / "blackbox_cases_1000.json"
DEFAULT_OUT = ROOT / "out" / "blackbox_packet_eval" / "results"
DEFAULT_VARIANTS = ["d-acca", "rule", "dd-rule", "spec-dd", "spec-dd-lazy", "helper-lazy", "bm25"]


def naive_bm25_select(router: MoMEMoCERouter, query: str, top_k: int) -> tuple[list[str], float, str]:
    started = time.perf_counter()
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return [], (time.perf_counter() - started) * 1000, "no_context_needed"
    rows: list[tuple[str, float]] = []
    avg_len = max(1.0, statistics.fmean(len(item.tokens) for item in router.items))
    doc_count = max(1, len(router.items))
    doc_freq: Counter[str] = Counter()
    for item in router.items:
        for token in set(item.tokens):
            doc_freq[token] += 1
    k1 = 1.25
    b = 0.72
    for item in router.items:
        score = 0.0
        dl = max(1, len(item.tokens))
        for token in q_tokens:
            tf = item.token_counts.get(token, 0)
            if not tf:
                continue
            idf = math.log(1 + (doc_count - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
            denom = tf + k1 * (1 - b + b * dl / avg_len)
            score += idf * (tf * (k1 + 1)) / denom
        if score > 0:
            rows.append((item.id, score))
    rows.sort(key=lambda row: row[1], reverse=True)
    selected = [item_id for item_id, _ in rows[:top_k]]
    latency = (time.perf_counter() - started) * 1000
    return selected, latency, "context_packet_ready" if selected else "no_context_needed"


def run_variant(
    *,
    variant: str,
    router: MoMEMoCERouter,
    case: dict[str, Any],
    max_union_items: int,
    top_k: int,
) -> dict[str, Any]:
    case_id = str(case["id"])
    query = str(case["query"])
    if variant == "d-acca":
        result, errors, _ = route_once(router, query, case_id=f"{case_id}__direct", artifact_dir=None)
        score = score_selection(case, result.selected_ids, result.decision, result.latency_ms)
        return {
            "score": score,
            "selected_ids": result.selected_ids,
            "decision": result.decision,
            "latency_ms": result.latency_ms,
            "artifact_errors": errors,
            "advice": None,
        }
    if variant == "bm25":
        selected_ids, latency_ms, decision = naive_bm25_select(router, query, top_k=top_k)
        score = score_selection(case, selected_ids, decision, latency_ms)
        return {
            "score": score,
            "selected_ids": selected_ids,
            "decision": decision,
            "latency_ms": latency_ms,
            "artifact_errors": [],
            "advice": None,
        }

    advice = build_advice(case, variant, router=router)
    bundle = route_librarian_bundle(
        router,
        advice,
        case_id=case_id,
        artifact_dir=None,
        max_union_items=max_union_items,
    )
    score = score_selection(case, bundle["selected_ids"], bundle["decision"], bundle["latency_ms"])
    return {
        "score": score,
        "selected_ids": bundle["selected_ids"],
        "decision": bundle["decision"],
        "latency_ms": bundle["latency_ms"],
        "artifact_errors": bundle["artifact_errors"],
        "advice": {
            "strategy": advice.strategy,
            "queries": advice.queries,
            "entity_terms": advice.entity_terms,
            "latency_ms": advice.latency_ms,
        },
    }


def summarize_variant(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["score"] for row in rows]
    latencies = [float(score["latency_ms"]) for score in scores]
    edge_scores = [row["score"] for row in rows if row["edge_case"]]
    normal_scores = [row["score"] for row in rows if not row["edge_case"]]
    return {
        "cases": len(rows),
        "passed": sum(1 for score in scores if score["passed"]),
        "quality": round(sum(1 for score in scores if score["passed"]) / len(scores), 4) if scores else 0.0,
        "edge_quality": round(sum(1 for score in edge_scores if score["passed"]) / len(edge_scores), 4) if edge_scores else 0.0,
        "normal_quality": round(sum(1 for score in normal_scores if score["passed"]) / len(normal_scores), 4) if normal_scores else 0.0,
        "forbidden_hits": sum(len(score["hit_forbidden"]) for score in scores),
        "mean_precision": round(statistics.fmean(float(score["evidence_precision"]) for score in scores), 4) if scores else 0.0,
        "mean_recall": round(statistics.fmean(float(score["evidence_recall"]) for score in scores), 4) if scores else 0.0,
        "latency_ms_mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "latency_ms_p95": round(sorted(latencies)[int(0.95 * (len(latencies) - 1))], 3) if latencies else 0.0,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    rows = [
        "# Black-Box D-ACCA Packet Eval",
        "",
        f"Created: {payload['created_at']}",
        f"Cases: {payload['case_count']} ({payload['edge_cases']} edge)",
        "",
        "| variant | quality | edge quality | forbidden | precision | recall | latency mean ms | latency p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in payload["summary"].items():
        rows.append(
            "| {variant} | {quality:.4f} | {edge:.4f} | {forbidden} | {precision:.4f} | {recall:.4f} | {lat:.3f} | {p95:.3f} |".format(
                variant=variant,
                quality=summary["quality"],
                edge=summary["edge_quality"],
                forbidden=summary["forbidden_hits"],
                precision=summary["mean_precision"],
                recall=summary["mean_recall"],
                lat=summary["latency_ms_mean"],
                p95=summary["latency_ms_p95"],
            )
        )
    return "\n".join(rows) + "\n"


def run_eval(
    *,
    cases_path: Path,
    out_dir: Path,
    variants: list[str],
    candidate_backend: str,
    top_k: int,
    max_union_items: int,
    limit: int | None = None,
) -> dict[str, Any]:
    cases = read_cases(cases_path)
    if limit is not None:
        cases = cases[:limit]
    routers: dict[Path, MoMEMoCERouter] = {}
    variant_rows: dict[str, list[dict[str, Any]]] = {variant: [] for variant in variants}
    for case in cases:
        dataset = resolve_path(Path(str(case["dataset"])))
        router = router_for_dataset(routers, dataset, top_k=top_k, candidate_backend=candidate_backend)
        for variant in variants:
            outcome = run_variant(
                variant=variant,
                router=router,
                case=case,
                max_union_items=max_union_items,
                top_k=top_k,
            )
            variant_rows[variant].append(
                {
                    "case_id": str(case["id"]),
                    "category": str(case.get("category", "")),
                    "edge_case": bool(case.get("edge_case", False)),
                    "query": str(case["query"]),
                    **outcome,
                }
            )
    payload = {
        "runner_version": "d_acca.blackbox_packet_eval.v0.1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cases_path": str(cases_path),
        "case_count": len(cases),
        "edge_cases": sum(1 for case in cases if case.get("edge_case")),
        "variants": variants,
        "candidate_backend": candidate_backend,
        "top_k": top_k,
        "summary": {variant: summarize_variant(rows) for variant, rows in variant_rows.items()},
        "results": variant_rows,
    }
    write_json(out_dir / "blackbox_packet_eval_results.json", payload)
    write_json(out_dir / "blackbox_packet_eval_summary.json", payload["summary"])
    write_text(out_dir / "blackbox_packet_eval_report.md", markdown_report(payload))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run black-box packet eval across D-ACCA variants and BM25.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--variants", nargs="+", default=DEFAULT_VARIANTS)
    parser.add_argument("--candidate-backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-union-items", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    payload = run_eval(
        cases_path=resolve_path(args.cases),
        out_dir=resolve_path(args.out),
        variants=args.variants,
        candidate_backend=args.candidate_backend,
        top_k=args.top_k,
        max_union_items=args.max_union_items,
        limit=args.limit,
    )
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
