from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, evaluate_case, load_cases, load_corpus, rough_tokens
    from run_baseline_comparison import top_bm25
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, evaluate_case, load_cases, load_corpus, rough_tokens
    from scripts.run_baseline_comparison import top_bm25


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_IDS = [
    "v2_01_ivy_001",
    "v2_01_cmd_001",
    "v2_01_safety_001",
    "v2_01_stale_001",
    "v2_01_adv_001",
    "v2_01_unans_001",
    "v2_cp8_speedup",
    "v2_cp9_overhead",
]


def prompt_from_evidence(query: str, evidence: list[dict[str, Any]]) -> str:
    lines = [
        "Answer the user query using only the evidence below. If the evidence is insufficient, abstain.",
        "",
        f"Query: {query}",
        "",
        "Evidence:",
    ]
    if not evidence:
        lines.append("(none)")
    for idx, row in enumerate(evidence, start=1):
        lines.append(f"[{idx}] id={row['id']} authority={row.get('authority')} staleness={row.get('staleness')}")
        lines.append(str(row.get("text", "")).replace("\n", " "))
    return "\n".join(lines)


def item_packet(row: Any) -> dict[str, Any]:
    text = row.text.replace("\n", " ")
    if len(text) > 900:
        text = text[:900] + "..."
    return {
        "id": row.id,
        "source_family": row.source_family,
        "authority": row.authority,
        "staleness": row.staleness,
        "safety_label": row.safety_label,
        "taint_labels": row.taint_labels,
        "exposure_policy": row.exposure_policy,
        "text": text,
    }


def run_demo(dataset: Path, *, case_ids: list[str], naive_top_k: int, backend: str) -> dict[str, Any]:
    items = load_corpus(dataset)
    item_by_id = {item.id: item for item in items}
    cases_by_id = {case["id"]: case for case in load_cases(dataset)}
    selected_cases = [cases_by_id[case_id] for case_id in case_ids if case_id in cases_by_id]
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)
    rows = []
    for case in selected_cases:
        query = case["query"]
        naive_ids = top_bm25(items, query, top_k=naive_top_k)
        naive_evidence = [item_packet(item_by_id[item_id]) for item_id in naive_ids if item_id in item_by_id]
        acca_result = router.route(query)
        evaluated = evaluate_case(case, acca_result)
        forbidden = set(case.get("forbidden_source_ids", []))
        rows.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "query": query,
                "required_source_ids": case.get("required_source_ids", []),
                "forbidden_source_ids": case.get("forbidden_source_ids", []),
                "no_memory": {
                    "prompt": prompt_from_evidence(query, []),
                    "prompt_tokens_est": rough_tokens(query),
                },
                "naive_bm25": {
                    "selected_ids": naive_ids,
                    "forbidden_hits": sorted(forbidden & set(naive_ids)),
                    "stale_or_decoy_ids": [
                        item_id
                        for item_id in naive_ids
                        if item_by_id[item_id].staleness in {"stale", "decoy"} or item_by_id[item_id].authority == "decoy"
                    ],
                    "prompt": prompt_from_evidence(query, naive_evidence),
                    "prompt_tokens_est": rough_tokens(prompt_from_evidence(query, naive_evidence)),
                },
                "acca_packet": {
                    "selected_ids": acca_result.selected_ids,
                    "passed_case_contract": evaluated["passed"],
                    "forbidden_hits": sorted(forbidden & set(acca_result.selected_ids)),
                    "answerability": acca_result.frontier_packet["answerability"],
                    "exposure_summary": acca_result.frontier_packet["exposure_summary"],
                    "frontier_packet": acca_result.frontier_packet,
                    "prompt": json.dumps(acca_result.frontier_packet, ensure_ascii=False, indent=2),
                    "prompt_tokens_est": rough_tokens(json.dumps(acca_result.frontier_packet, ensure_ascii=False)),
                },
            }
        )
    return {
        "runner_version": "model_facing_demo.v0.1",
        "dataset": str(dataset),
        "backend": backend,
        "naive_top_k": naive_top_k,
        "cases": len(rows),
        "rows": rows,
        "summary": {
            "acca_passed": sum(1 for row in rows if row["acca_packet"]["passed_case_contract"]),
            "naive_forbidden_hits": sum(len(row["naive_bm25"]["forbidden_hits"]) for row in rows),
            "acca_forbidden_hits": sum(len(row["acca_packet"]["forbidden_hits"]) for row in rows),
            "acca_forbidden_selected": sum(row["acca_packet"]["exposure_summary"]["forbidden_selected"] for row in rows),
        },
    }


def markdown(payload: dict[str, Any]) -> str:
    rows = [
        "| case | category | naive ids | naive bad | ACCA ids | answerability | ACCA pass |",
        "|---|---|---|---|---|---|---:|",
    ]
    for row in payload["rows"]:
        naive_bad = [*row["naive_bm25"]["forbidden_hits"], *row["naive_bm25"]["stale_or_decoy_ids"]]
        rows.append(
            f"| {row['case_id']} | {row['category']} | `{', '.join(row['naive_bm25']['selected_ids'])}` | "
            f"`{', '.join(naive_bad)}` | `{', '.join(row['acca_packet']['selected_ids'])}` | "
            f"{row['acca_packet']['answerability']} | {row['acca_packet']['passed_case_contract']} |"
        )
    return "\n".join(
        [
            "# Model-Facing Packet Demo",
            "",
            f"Dataset: `{payload['dataset']}`",
            f"Backend: `{payload['backend']}`",
            "",
            *rows,
            "",
            "The JSON output contains the actual no-memory prompt, naive BM25 prompt, and ACCA frontier packet prompt for each case.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build model-facing prompt artifacts for no-memory, naive BM25, and ACCA packet modes.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ivy_real_v2")
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--naive-top-k", type=int, default=5)
    parser.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    case_ids = args.case_id or DEFAULT_CASE_IDS
    payload = run_demo(dataset, case_ids=case_ids, naive_top_k=args.naive_top_k, backend=args.backend)
    output_json = args.output_json or ROOT / "out" / f"model_facing_demo_{dataset.name}.json"
    output_md = args.output_md or ROOT / "out" / f"model_facing_demo_{dataset.name}.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(output_json), "output_md": str(output_md), "summary": payload["summary"]}, indent=2))
    return 0 if payload["summary"]["acca_passed"] == payload["cases"] and payload["summary"]["acca_forbidden_hits"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
