from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus, norm
except ModuleNotFoundError:
    from scripts.mome_moce_harness import MoMEMoCERouter, load_cases, load_corpus, norm


ROOT = Path(__file__).resolve().parents[1]


VARIANTS = [
    "compact_default",
    "answer_first",
    "evidence_first",
    "contradiction_aware",
    "proof_lite",
]


def _one_line(value: str) -> str:
    return " ".join(str(value).split())


def _evidence_lines(packet: dict[str, Any]) -> list[str]:
    lines = []
    for item in packet.get("evidence", []):
        lines.append(
            f"- [{item['id']}] authority={item['authority']} staleness={item['staleness']} "
            f"family={item['source_family']} text={_one_line(item.get('text', ''))}"
        )
    return lines


def _rejected_lines(proof: dict[str, Any], *, limit: int = 6) -> list[str]:
    lines = []
    for item in proof.get("rejected_evidence", [])[:limit]:
        lines.append(
            f"- rejected [{item.get('id')}] reason={item.get('reason')} "
            f"authority={item.get('authority')} staleness={item.get('staleness')}"
        )
    return lines


def _conflict_lines(proof: dict[str, Any]) -> list[str]:
    lines = []
    for pair in proof.get("conflict_pairs", []):
        lines.append(
            f"- conflict: {pair.get('left')} vs {pair.get('right')} "
            f"resolution={pair.get('resolution', 'surface_or_prefer_authoritative_current')}"
        )
    return lines


def render_variant(variant: str, *, case: dict[str, Any], result: Any) -> str:
    packet = result.frontier_packet
    proof = result.route_proof
    evidence = _evidence_lines(packet)
    rejected = _rejected_lines(proof)
    conflicts = _conflict_lines(proof)
    answerability = packet.get("answerability", "unknown")

    if variant == "compact_default":
        lines = [
            "ACCA CONTEXT PACKET",
            f"query: {packet['query']}",
            f"answerability: {answerability}",
            packet["instruction"],
            "evidence:",
            *(evidence or ["- none; abstain if factual context is required"]),
        ]
    elif variant == "answer_first":
        lines = [
            "ANSWER GUIDANCE",
            f"answerability: {answerability}",
            "Use only cited selected evidence; abstain if selected evidence is empty.",
            "selected citations: " + ", ".join(result.selected_ids or ["none"]),
            "task query: " + packet["query"],
            "evidence:",
            *(evidence or ["- none"]),
        ]
    elif variant == "evidence_first":
        lines = [
            "SELECTED EVIDENCE",
            *(evidence or ["- none"]),
            "QUERY",
            packet["query"],
            "CONSTRAINTS",
            *packet.get("constraints", []),
            f"answerability: {answerability}",
        ]
    elif variant == "contradiction_aware":
        lines = [
            "D-ACCA CONTRADICTION-AWARE PACKET",
            f"query: {packet['query']}",
            f"answerability: {answerability}",
            "selected evidence is authoritative context; rejected stale, decoy, or forbidden evidence is not authority.",
            "selected evidence:",
            *(evidence or ["- none; abstain because there is no authoritative selected evidence"]),
            "conflict / ambiguity surface:",
            *(conflicts or ["- no selected conflict pair"]),
            "rejected or unsafe evidence:",
            *(rejected or ["- none"]),
            "exposure summary: " + json.dumps(proof.get("exposure_summary", {}), sort_keys=True),
        ]
    elif variant == "proof_lite":
        lines = [
            "ROUTE PROOF LITE",
            f"decision: {proof.get('decision')}",
            f"answerability: {answerability}",
            "authority chain: " + ", ".join(proof.get("authority_chain", []) or ["none"]),
            "selected evidence:",
            *(evidence or ["- none"]),
            "rejected evidence:",
            *(rejected[:3] or ["- none"]),
            "Use selected evidence only; abstain without selected evidence.",
        ]
    else:
        raise ValueError(f"unknown packet variant: {variant}")
    return "\n".join(lines)


def score_rendered(case: dict[str, Any], result: Any, rendered: str) -> dict[str, Any]:
    text = norm(rendered)
    required = set(case.get("required_source_ids", []))
    forbidden = set(case.get("forbidden_source_ids", []))
    selected = set(result.selected_ids)
    required_visible = sorted(item_id for item_id in required if item_id.lower() in text)
    missing_required = sorted(required - set(required_visible))
    forbidden_authority_visible = sorted(item_id for item_id in forbidden if item_id in selected and item_id.lower() in text)
    selected_forbidden = sorted(forbidden & selected)
    must_abstain = bool(case.get("must_abstain", False))
    abstention_visible = any(term in text for term in ["abstain", "no authoritative selected evidence", "none"])
    safety_case = bool(case.get("requires_safety_priority", False))
    safety_visible = any(term in text for term in ["safety", "forbidden", "unsafe", "policy", "advisory"])
    conflict_case = bool(case.get("requires_conflict_resolution", False))
    conflict_terms_visible = any(term in text for term in ["conflict", "contradict", "ambiguity", "rejected", "stale", "decoy"])
    conflict_pairs = result.route_proof.get("conflict_pairs", [])
    conflict_pair_visible = any(
        str(pair.get("left", "")).lower() in text and str(pair.get("right", "")).lower() in text
        for pair in conflict_pairs
    )
    if conflict_case and len(required) > 1:
        conflict_pair_visible = conflict_pair_visible or all(item_id.lower() in text for item_id in required)
    evidence_pass = not missing_required and not selected_forbidden and not forbidden_authority_visible
    abstention_pass = (not must_abstain) or (not selected and abstention_visible)
    safety_pass = (not safety_case) or safety_visible
    conflict_pass = (not conflict_case) or (conflict_terms_visible and (conflict_pair_visible or not conflict_pairs))
    words = len(rendered.split())
    passed = evidence_pass and abstention_pass and safety_pass and conflict_pass
    return {
        "passed": bool(passed),
        "quality_points": sum(bool(x) for x in [evidence_pass, abstention_pass, safety_pass, conflict_pass]) / 4,
        "words": words,
        "missing_required": missing_required,
        "selected_forbidden": selected_forbidden,
        "forbidden_authority_visible": forbidden_authority_visible,
        "abstention_pass": abstention_pass,
        "safety_pass": safety_pass,
        "conflict_pass": conflict_pass,
    }


def run_eval(dataset: Path, *, backend: str = "indexed", limit: int | None = None) -> dict[str, Any]:
    items = load_corpus(dataset)
    cases = load_cases(dataset)
    selected_cases = cases[:limit] if limit else cases
    router = MoMEMoCERouter(items, candidate_backend=backend, dataset_path=dataset)

    rows = []
    variant_results: dict[str, list[dict[str, Any]]] = {variant: [] for variant in VARIANTS}
    for case in selected_cases:
        routed = router.route(case["query"])
        routed.route_proof["case_id"] = case["id"]
        routed.frontier_packet["case_id"] = case["id"]
        row = {
            "case_id": case["id"],
            "category": case["category"],
            "selected_ids": routed.selected_ids,
            "variants": {},
        }
        for variant in VARIANTS:
            rendered = render_variant(variant, case=case, result=routed)
            score = score_rendered(case, routed, rendered)
            score["preview"] = rendered[:700]
            row["variants"][variant] = score
            variant_results[variant].append(score)
        rows.append(row)

    summary = {}
    for variant, scores in variant_results.items():
        passed = sum(1 for score in scores if score["passed"])
        conflict_scores = [score for row in rows for name, score in row["variants"].items() if name == variant and row["category"] == "stale_conflict"]
        summary[variant] = {
            "passed": passed,
            "cases": len(scores),
            "quality": round(passed / len(scores), 4) if scores else 0.0,
            "avg_quality_points": round(statistics.fmean(score["quality_points"] for score in scores), 4) if scores else 0.0,
            "avg_words": round(statistics.fmean(score["words"] for score in scores), 1) if scores else 0.0,
            "conflict_pass_rate": round(
                sum(1 for score in conflict_scores if score["conflict_pass"]) / len(conflict_scores), 4
            )
            if conflict_scores
            else 1.0,
        }
    best_variant = sorted(
        summary,
        key=lambda name: (
            summary[name]["quality"],
            summary[name]["conflict_pass_rate"],
            -summary[name]["avg_words"],
        ),
        reverse=True,
    )[0]
    return {
        "runner_version": "cp24.packet_format_ab.v0.1",
        "dataset": str(dataset),
        "backend": backend,
        "variants": VARIANTS,
        "best_variant": best_variant,
        "summary": summary,
        "rows": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CP24 Packet Format A/B",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Backend: `{payload['backend']}`",
        f"- Best variant: `{payload['best_variant']}`",
        "",
        "| Variant | Passed | Cases | Quality | Conflict Pass | Avg Words |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for variant, summary in payload["summary"].items():
        lines.append(
            f"| `{variant}` | {summary['passed']} | {summary['cases']} | {summary['quality']:.4f} | "
            f"{summary['conflict_pass_rate']:.4f} | {summary['avg_words']:.1f} |"
        )
    lines.extend(
        [
            "",
            "The score is a deterministic downstream-usability proxy. It rewards rendered packets that preserve required citations, avoid forbidden authority, make abstention explicit, surface safety posture, and show conflict context when the case demands ambiguity handling.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP24 deterministic packet-format A/B eval.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "out" / "context_stress_ambiguity_cp22")
    parser.add_argument("--backend", choices=["scan", "indexed", "rust"], default="indexed")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=ROOT / "out" / "cp24_packet_format_ab.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "out" / "cp24_packet_format_ab.md")
    args = parser.parse_args(argv)

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    payload = run_eval(dataset, backend=args.backend, limit=args.limit)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md), "best_variant": payload["best_variant"], "summary": payload["summary"]}, indent=2))
    best = payload["summary"][payload["best_variant"]]
    return 0 if payload["best_variant"] == "contradiction_aware" and best["quality"] >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
