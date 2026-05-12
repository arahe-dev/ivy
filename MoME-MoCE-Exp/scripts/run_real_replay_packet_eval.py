from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from generate_real_replay_packet_cases import DEFAULT_CASES, DEFAULT_DATASET, DEFAULT_SESSIONS_ROOT, main as generate_main
    from run_blackbox_packet_eval import run_eval
    from run_librarian_advisor_harness import resolve_path, write_json, write_text
except ModuleNotFoundError:
    from scripts.generate_real_replay_packet_cases import (
        DEFAULT_CASES,
        DEFAULT_DATASET,
        DEFAULT_SESSIONS_ROOT,
        main as generate_main,
    )
    from scripts.run_blackbox_packet_eval import run_eval
    from scripts.run_librarian_advisor_harness import resolve_path, write_json, write_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "real_replay_packet_eval" / "results_top3_1000"
TOP3_VARIANTS = ["helper-lazy", "d-acca", "spec-dd"]


def load_case_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def category_breakdown(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("category", ""))].append(row)
    out: dict[str, dict[str, Any]] = {}
    for category, items in sorted(buckets.items()):
        scores = [item["score"] for item in items]
        passed = sum(1 for score in scores if score["passed"])
        out[category] = {
            "cases": len(items),
            "quality": round(passed / len(items), 4) if items else 0.0,
            "forbidden_hits": sum(len(score["hit_forbidden"]) for score in scores),
            "mean_latency_ms": round(statistics.fmean(float(score["latency_ms"]) for score in scores), 3) if scores else 0.0,
        }
    return out


def failure_digest(rows: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        score = row["score"]
        if score["passed"]:
            continue
        failures.append(
            {
                "case_id": row["case_id"],
                "category": row["category"],
                "decision": score["decision"],
                "missing_required": score["missing_required"],
                "hit_forbidden": score["hit_forbidden"],
                "selected_ids": score["selected_ids"],
                "query_preview": str(row.get("query", ""))[:180],
            }
        )
        if len(failures) >= limit:
            break
    return failures


def replay_report(payload: dict[str, Any], case_payload: dict[str, Any], extended: dict[str, Any]) -> str:
    lines = [
        "# D-ACCA Real Replay Packet Eval",
        "",
        f"Created: {payload['created_at']}",
        f"Cases: {payload['case_count']} ({payload['edge_cases']} edge)",
        f"Case source: `{payload['cases_path']}`",
        "",
        "## What This Tests",
        "",
        "This harness derives black-box packet cases from real Codex user turns, then applies a fixed internal bank of organic rewrites: raw, current-only, agent-packet, stale-guard, slang, follow-up, and typo variants. The variation bank is intentionally not exposed as a template grid, because the point is to pressure the router with messy replay phrasing rather than tune a benchmark parameter.",
        "",
        "Raw private session logs are not committed. The generated cases are derived/redacted artifacts under `out/`.",
        "",
        "## Top-3 Candidate Variants",
        "",
        "| variant | reason included |",
        "|---|---|",
        "| helper-lazy | strongest current learned-alias/profile candidate |",
        "| d-acca | core deterministic admission baseline that survived replay selection better than narrow DD rules |",
        "| spec-dd | speculative draft/verify candidate with better replay selection than the lazy/narrow rule variants |",
        "",
        "## Summary",
        "",
        "| variant | quality | edge quality | forbidden | precision | recall | latency mean ms | latency p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in payload["summary"].items():
        lines.append(
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
    generation = case_payload.get("generation", {})
    lines.extend(
        [
            "",
            "## Replay Source Mix",
            "",
            f"- Session user turns seen: `{generation.get('session_user_turns_seen', 0)}`",
            f"- Matched user turns: `{generation.get('matched_user_turns', 0)}`",
            f"- Fixed variation bank: `{', '.join(generation.get('variation_bank', []))}`",
            f"- Parameterized variations: `{generation.get('parameterized_variations', False)}`",
            "",
            "| concept | matched source turns |",
            "|---|---:|",
        ]
    )
    for concept, count in sorted(dict(generation.get("matched_concepts", {})).items()):
        lines.append(f"| {concept} | {count} |")

    lines.extend(["", "## Category Quality", ""])
    for variant, breakdown in extended["category_breakdown"].items():
        lines.extend([f"### {variant}", "", "| category | cases | quality | forbidden | mean latency ms |", "|---|---:|---:|---:|---:|"])
        for category, row in breakdown.items():
            lines.append(
                f"| {category} | {row['cases']} | {row['quality']:.4f} | {row['forbidden_hits']} | {row['mean_latency_ms']:.3f} |"
            )
        lines.append("")

    lines.extend(["## Failure Samples", ""])
    for variant, failures in extended["failure_digest"].items():
        lines.append(f"### {variant}")
        if not failures:
            lines.extend(["", "No failures in this run.", ""])
            continue
        lines.extend(["", "| case | category | missing | forbidden | selected | query preview |", "|---|---|---|---|---|---|"])
        for failure in failures:
            lines.append(
                "| {case} | {category} | `{missing}` | `{forbidden}` | `{selected}` | {query} |".format(
                    case=failure["case_id"],
                    category=failure["category"],
                    missing=", ".join(failure["missing_required"]),
                    forbidden=", ".join(failure["hit_forbidden"]),
                    selected=", ".join(failure["selected_ids"]),
                    query=str(failure["query_preview"]).replace("|", "/"),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "This is closer to a real-world replay test than the previous synthetic packet because the source turns come from actual Codex sessions. It is still auto-labeled: expected evidence comes from a curated ACCA concept catalog, not manual human judgment. That makes it useful for finding router brittleness, but not sufficient as final product proof.",
            "",
            "The next harder version should add human-reviewed labels for the most ambiguous 50-100 replay cases and a metadata-ablation pass that removes helper aliases from a fraction of the corpus.",
            "",
        ]
    )
    return "\n".join(lines)


def run_replay_eval(
    *,
    sessions_root: Path,
    cases_path: Path,
    dataset: Path,
    out_dir: Path,
    count: int,
    seed: int,
    variants: list[str],
    candidate_backend: str,
    top_k: int,
    max_union_items: int,
) -> dict[str, Any]:
    cases_path = resolve_path(cases_path)
    dataset = resolve_path(dataset)
    out_dir = resolve_path(out_dir)
    generate_main(
        [
            "--sessions-root",
            str(sessions_root),
            "--count",
            str(count),
            "--seed",
            str(seed),
            "--dataset",
            str(dataset),
            "--cases-out",
            str(cases_path),
        ]
    )
    payload = run_eval(
        cases_path=cases_path,
        out_dir=out_dir,
        variants=variants,
        candidate_backend=candidate_backend,
        top_k=top_k,
        max_union_items=max_union_items,
        limit=None,
    )
    case_payload = load_case_payload(cases_path)
    extended = {
        "category_breakdown": {variant: category_breakdown(rows) for variant, rows in payload["results"].items()},
        "failure_digest": {variant: failure_digest(rows) for variant, rows in payload["results"].items()},
        "variant_ranking": [
            variant
            for variant, _summary in sorted(
                payload["summary"].items(),
                key=lambda item: (
                    item[1]["quality"],
                    -item[1]["forbidden_hits"],
                    -item[1]["latency_ms_p95"],
                ),
                reverse=True,
            )
        ],
        "category_counts": dict(Counter(case["category"] for case in case_payload.get("cases", []))),
    }
    payload["runner_version"] = "d_acca.real_replay_packet_eval.v0.1"
    payload["replay_generation"] = case_payload.get("generation", {})
    payload["extended_summary"] = extended
    write_json(out_dir / "real_replay_packet_eval_results.json", payload)
    write_json(out_dir / "real_replay_packet_eval_summary.json", payload["summary"])
    write_text(out_dir / "real_replay_packet_eval_report.md", replay_report(payload, case_payload, extended))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run real Codex replay packet eval on top D-ACCA variants.")
    parser.add_argument("--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260512)
    parser.add_argument("--variants", nargs="+", default=TOP3_VARIANTS)
    parser.add_argument("--candidate-backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-union-items", type=int, default=2)
    args = parser.parse_args(argv)

    payload = run_replay_eval(
        sessions_root=args.sessions_root,
        cases_path=args.cases,
        dataset=args.dataset,
        out_dir=args.out,
        count=args.count,
        seed=args.seed,
        variants=args.variants,
        candidate_backend=args.candidate_backend,
        top_k=args.top_k,
        max_union_items=args.max_union_items,
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
