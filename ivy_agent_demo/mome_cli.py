from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory_packet import to_dict, to_json
from .memory_packet_cli import build_synthetic_memory, packet_quality_score
from .memory_store import DEFAULT_DB_PATH
from .mome_packet import build_mome_packet, mome_packet_payload
from .mome_policy import list_mome_policies, load_mome_policy
from .mome_router import route_mome


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/mome_preview")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def save_preview(packet: Any, metadata: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "packet.txt").write_text(packet.packet_text, encoding="utf-8")
    (out_dir / "packet.json").write_text(json.dumps(mome_packet_payload(packet, metadata), indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "candidates.json").write_text(to_json(packet.candidates_considered), encoding="utf-8")
    (out_dir / "routing.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(packet, metadata, out_dir / "report.md")


def write_report(packet: Any, metadata: dict[str, Any], path: Path) -> None:
    lines = [
        "# IVY MoME Preview",
        "",
        f"- Query: `{packet.query}`",
        f"- Task type: `{metadata.get('task_type')}`",
        f"- Policy: `{metadata.get('policy_name')}`",
        f"- Experts used: `{metadata.get('experts_used')}`",
        f"- Candidate count: `{metadata.get('candidate_count')}`",
        f"- Packet decision: `{metadata.get('packet_decision')}`",
        f"- Injection allowed by policy: `{metadata.get('injection_allowed')}`",
        f"- Latency ms: `{metadata.get('latency_ms')}`",
        "",
        "## Packet",
        "",
        "```text",
        packet.packet_text,
        "```",
        "",
        "## Contributions",
        "",
        f"- Expert contribution counts: `{metadata.get('expert_contribution_counts')}`",
        f"- Source family counts: `{metadata.get('source_family_counts')}`",
        f"- Exact match terms: `{metadata.get('exact_match_terms')}`",
        f"- Caution rules: `{metadata.get('caution_rules_applied')}`",
        "",
        "## Candidates",
        "",
        "| rank | id | expert | family | kind | score | terms | source | text |",
        "|---:|---:|---|---|---|---:|---|---|---|",
    ]
    for index, candidate in enumerate(packet.candidates_considered[:20], start=1):
        ranking = candidate.ranking or {}
        source = str(candidate.source_artifact_path or "").replace("|", "/")
        text = candidate.text[:140].replace("|", "/")
        terms = ",".join(ranking.get("matched_terms", []))
        lines.append(f"| {index} | {candidate.memory_item_id or ''} | {candidate.source_expert} | {candidate.source_family} | {candidate.kind or ''} | {candidate.score} | {terms} | {source} | {text} |")
    if metadata.get("warnings"):
        lines += ["", "## Warnings", ""]
        lines.extend(f"- {warning}" for warning in metadata["warnings"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_preview(args: argparse.Namespace) -> tuple[Any, dict[str, Any], Path | None]:
    packet, metadata = build_mome_packet(
        query=args.query,
        db_path=args.db,
        policy_name=args.policy,
        top_k=args.top_k,
        max_packet_chars=args.max_packet_chars,
        require_provenance=args.require_provenance,
    )
    out_dir = None
    if not args.no_save:
        out_dir = Path(args.output_root or DEFAULT_OUTPUT_ROOT) / timestamp()
        save_preview(packet, metadata, out_dir)
    return packet, metadata, out_dir


def run_compare(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Path]:
    out_dir = Path(args.output_root or DEFAULT_OUTPUT_ROOT) / timestamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for policy in args.policies:
        packet, metadata = build_mome_packet(args.query, args.db, policy, args.top_k, args.max_packet_chars, args.require_provenance)
        save_preview(packet, metadata, out_dir / policy)
        metrics = to_dict(packet.metrics)
        metrics["packet_quality_score"] = packet_quality_score(metrics)
        rows.append({"policy": policy, "metadata": metadata, "metrics": metrics, "packet_text": packet.packet_text})
    (out_dir / "comparison_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# IVY MoME Policy Comparison",
        "",
        f"- Query: `{args.query}`",
        "",
        "| policy | task_type | experts | chars | lines | evidence | provenance | quality |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        meta = row["metadata"]
        metrics = row["metrics"]
        lines.append(f"| {row['policy']} | {meta.get('task_type')} | {','.join(meta.get('experts_used', []))} | {metrics['packet_chars']} | {metrics['packet_line_count']} | {metrics['evidence_count']} | {metrics['provenance_line_rate']} | {metrics['packet_quality_score']} |")
    if rows:
        lines += ["", "## Summary", ""]
        lines.append(f"- Best quality score: `{max(rows, key=lambda r: r['metrics']['packet_quality_score'])['policy']}`")
        lines.append(f"- Most compact: `{min(rows, key=lambda r: r['metrics']['packet_chars'])['policy']}`")
    (out_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows, out_dir


def run_diagnose(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    route = route_mome(args.query, args.db, args.policy, args.top_k, args.max_packet_chars, args.require_provenance)
    out_dir = Path(args.output_root or DEFAULT_OUTPUT_ROOT) / timestamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, candidate in enumerate(route.candidates[: int(args.top_k or 10)], start=1):
        rows.append({
            "rank": index,
            "memory_item_id": candidate.memory_item_id,
            "kind": candidate.kind,
            "source_expert": candidate.source_expert,
            "source_family": candidate.source_family,
            "final_score": candidate.score,
            "matched_terms": ",".join((candidate.ranking or {}).get("matched_terms", [])),
            "source_artifact_path": candidate.source_artifact_path,
            "text_short": candidate.text[:220],
            "ranking": candidate.ranking,
        })
    payload = {"metadata": route.metadata, "decision": to_dict(route.decision), "rows": rows}
    (out_dir / "diagnostics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["rank", "memory_item_id", "kind", "source_expert", "source_family", "final_score", "matched_terms", "source_artifact_path", "text_short"]
    with (out_dir / "diagnostics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    lines = [
        "# IVY MoME Routing Diagnostics",
        "",
        f"- Query: `{args.query}`",
        f"- Task type: `{route.metadata.get('task_type')}`",
        f"- Policy: `{route.metadata.get('policy_name')}`",
        f"- Experts: `{route.metadata.get('experts_used')}`",
        "",
        "| rank | id | expert | family | score | matched | source | text |",
        "|---:|---:|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['rank']} | {row.get('memory_item_id') or ''} | {row.get('source_expert')} | {row.get('source_family')} | {row.get('final_score')} | {row.get('matched_terms')} | {str(row.get('source_artifact_path') or '').replace('|', '/')} | {str(row.get('text_short') or '').replace('|', '/')} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload, out_dir


def self_test() -> int:
    failures: list[str] = []
    out_root = DEFAULT_OUTPUT_ROOT / f"selftest_{timestamp()}"
    out_root.mkdir(parents=True, exist_ok=True)
    db = out_root / "synthetic_memory.sqlite3"
    build_synthetic_memory(db)
    for name in ("mome_none", "mome_hybrid_default", "mome_debug", "mome_benchmark", "mome_safety", "mome_workflow", "mome_runbook", "mome_auto"):
        try:
            load_mome_policy(name)
        except Exception as exc:
            failures.append(f"policy failed to load {name}: {exc}")
    checks = [
        ("json tool call failed because qwen emitted think tags", "mome_debug", ["failure_debug", "exact_keyword"], ["think", "json", "validation"]),
        ("benchmark qwen 4060 ctx 512 decode_tps", "mome_benchmark", ["benchmark", "exact_keyword"], ["qwen", "ctx=512", "decode_tps"]),
        ("absolute path policy violation sandbox", "mome_safety", ["safety_policy", "exact_keyword"], ["path", "policy", "sandbox"]),
        ("successful calc write workflow", "mome_workflow", ["workflow_procedure", "exact_keyword"], ["calc", "write"]),
    ]
    for query, policy, expected_experts, expected_terms in checks:
        packet, metadata = build_mome_packet(query, db, policy, top_k=5, max_packet_chars=1400)
        save_preview(packet, metadata, out_root / policy)
        blob = packet.packet_text.lower()
        if not all(expert in metadata["experts_used"] for expert in expected_experts):
            failures.append(f"missing experts for {policy}: {metadata['experts_used']}")
        if not all(term.lower() in blob for term in expected_terms):
            failures.append(f"missing packet terms for {policy}: {expected_terms}")
        if not packet.candidates_considered:
            failures.append(f"no candidates for {policy}")
        if packet.metrics.packet_chars > 1400:
            failures.append(f"packet too large for {policy}")
    none_packet, none_meta = build_mome_packet("anything", db, "mome_none", top_k=5)
    if none_packet.packet_lines:
        failures.append("mome_none selected packet lines")
    rows, compare_dir = run_compare(argparse.Namespace(query="benchmark qwen 4060 ctx 512 decode_tps", policies=["mome_none", "mome_benchmark", "mome_auto"], db=str(db), top_k=5, max_packet_chars=1400, output_root=str(out_root), require_provenance=False))
    if len(rows) != 3 or not (compare_dir / "comparison_results.json").exists():
        failures.append("compare did not write expected artifacts")
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        print(f"artifacts: {out_root}")
        return 1
    print("PASS")
    print(f"artifacts: {out_root}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="IVY MoME v0 preview and diagnostics.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parent.add_argument("--policy", default="mome_auto")
    parent.add_argument("--top-k", type=int, default=5)
    parent.add_argument("--max-packet-chars", type=int)
    parent.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parent.add_argument("--json", action="store_true")
    parent.add_argument("--no-save", action="store_true")
    parent.add_argument("--require-provenance", action="store_true")

    p_preview = sub.add_parser("preview", parents=[parent])
    p_preview.add_argument("--query", required=True)

    p_compare = sub.add_parser("compare", parents=[parent])
    p_compare.add_argument("--query", required=True)
    p_compare.add_argument("--policies", nargs="+", required=True)

    p_diag = sub.add_parser("diagnose", parents=[parent])
    p_diag.add_argument("--query", required=True)

    sub.add_parser("self-test")
    sub.add_parser("list-policies")
    args = parser.parse_args()

    if args.cmd == "self-test":
        raise SystemExit(self_test())
    if args.cmd == "list-policies":
        for name in list_mome_policies():
            print(name)
        return
    if args.cmd == "preview":
        packet, metadata, out_dir = run_preview(args)
        if args.json:
            print(json.dumps(mome_packet_payload(packet, metadata), indent=2, ensure_ascii=False))
        else:
            print(packet.packet_text)
            if out_dir:
                print(f"\nSaved MoME preview: {out_dir}")
        return
    if args.cmd == "compare":
        rows, out_dir = run_compare(args)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print(f"Saved MoME comparison: {out_dir}")
        return
    if args.cmd == "diagnose":
        payload, out_dir = run_diagnose(args)
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            meta = payload["metadata"]
            print(f"task_type: {meta.get('task_type')}")
            print(f"policy: {meta.get('policy_name')}")
            print(f"experts: {meta.get('experts_used')}")
            for row in payload["rows"]:
                print(f"{row['rank']}. id={row.get('memory_item_id')} expert={row.get('source_expert')} family={row.get('source_family')} score={row.get('final_score')} terms={row.get('matched_terms')}")
                print(f"   source={row.get('source_artifact_path')}")
                print(f"   {row.get('text_short')}")
            print(f"Saved MoME diagnostics: {out_dir}")


if __name__ == "__main__":
    main()
