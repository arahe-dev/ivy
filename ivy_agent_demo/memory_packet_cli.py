from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .context_packet import compose_packet
from .memory_packet import MemoryPacket, to_dict, to_json
from .memory_router import classify_task, load_policy, route_memory
from .memory_search import vectorize_memory_items
from .memory_store import DEFAULT_DB_PATH, MemoryStore


DEFAULT_OUTPUT_ROOT = Path("C:/ivy/runs/memory_packet_preview")
DIAGNOSTIC_OUTPUT_ROOT = Path("C:/ivy/runs/memory_ranking_diagnostics")


def run_preview(
    query: str,
    db_path: str | Path | None = None,
    policy: str | None = None,
    top_k: int | None = None,
    max_packet_chars: int | None = None,
    output_root: str | Path | None = None,
    save: bool = True,
    require_provenance: bool | None = None,
) -> tuple[MemoryPacket, Path | None]:
    start = time.perf_counter()
    decision, candidates, policy_doc = route_memory(query, db_path, policy, top_k, max_packet_chars, require_provenance)
    latency_ms = (time.perf_counter() - start) * 1000.0
    packet = compose_packet(query, decision, candidates, latency_ms=latency_ms, policy=policy_doc)
    out_dir = None
    if save:
        out_dir = Path(output_root or DEFAULT_OUTPUT_ROOT) / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        save_packet(packet, out_dir)
    return packet, out_dir


def save_packet(packet: MemoryPacket, out_dir: Path, suffix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"packet{suffix}"
    (out_dir / f"{stem}.txt").write_text(packet.packet_text, encoding="utf-8")
    (out_dir / f"{stem}.json").write_text(to_json(packet), encoding="utf-8")
    (out_dir / f"candidates{suffix}.json").write_text(to_json(packet.candidates_considered), encoding="utf-8")
    (out_dir / f"routing_decision{suffix}.json").write_text(to_json(packet.routing_decision), encoding="utf-8")
    write_packet_report(packet, out_dir / f"packet_report{suffix}.md")


def write_packet_report(packet: MemoryPacket, path: Path) -> None:
    warnings = []
    if any(not line.provenance_present for line in packet.packet_lines):
        warnings.append("missing provenance on one or more packet lines")
    if packet.metrics.truncated:
        warnings.append("packet truncated")
    if packet.metrics.evidence_count <= 1 and packet.metrics.packet_line_count > 0:
        warnings.append("sparse evidence")
    if packet.task_type == "benchmark":
        warnings.append("single-run benchmark data is smoke evidence, not a stable performance claim")
    lines = [
        "# Memory Packet Preview",
        "",
        f"- Query: `{packet.query}`",
        f"- Task type: `{packet.task_type}`",
        f"- Policy: `{packet.policy}`",
        f"- Experts: `{packet.routing_decision.selected_experts}`",
        f"- Composers: `{packet.routing_decision.selected_composers}`",
        f"- Candidates considered: `{packet.metrics.candidate_count}`",
        f"- Packet lines: `{packet.metrics.packet_line_count}`",
        f"- Packet chars: `{packet.metrics.packet_chars}`",
        f"- Provenance line rate: `{packet.metrics.provenance_line_rate}`",
        f"- Latency ms: `{packet.metrics.latency_ms}`",
        f"- Truncated: `{packet.metrics.truncated}`",
        "",
        "## Packet",
        "",
        "```text",
        packet.packet_text,
        "```",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in to_dict(packet.metrics).items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Grouped Evidence",
        "",
        "| kind | summary | evidence_count | examples | memory_item_ids |",
        "|---|---|---:|---|---|",
    ]
    for group in packet.candidate_groups:
        examples = "<br>".join(group.example_artifacts[:3]).replace("|", "/")
        ids = ", ".join(str(x) for x in group.grouped_memory_item_ids)
        lines.append(f"| {group.kind or ''} | {group.summary.replace('|', '/')} | {group.evidence_count} | {examples} | {ids} |")
    lines += [
        "",
        "## Raw Candidates",
        "",
        "| id | kind | expert | score | provenance | text |",
        "|---:|---|---|---:|---|---|",
    ]
    for candidate in packet.candidates_considered:
        lines.append(f"| {candidate.memory_item_id or ''} | {candidate.kind or ''} | {candidate.source_expert} | {candidate.score} | {candidate.provenance_present} | {candidate.text[:120].replace('|', '/')} |")
    lines += ["", "## Warnings", ""]
    lines.extend([f"- {warning}" for warning in warnings] if warnings else ["- None."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def packet_quality_score(metrics: dict[str, Any]) -> float:
    evidence_norm = min(float(metrics.get("evidence_count", 0)) / 5.0, 1.0)
    kind_bonus = min(float(metrics.get("unique_kind_count", 0)) * 0.1, 0.3)
    chars_penalty = min(float(metrics.get("chars_per_evidence", 999)) / 1000.0, 1.0) * 0.4
    repetitive_penalty = 0.25 if metrics.get("duplicate_group_count", 0) == 0 and metrics.get("raw_candidate_count", 0) > metrics.get("packet_line_count", 0) else 0.0
    missing_prov_penalty = 0.3 if float(metrics.get("provenance_line_rate", 0.0)) < 1.0 else 0.0
    return round(float(metrics.get("provenance_line_rate", 0.0)) + evidence_norm + kind_bonus - chars_penalty - repetitive_penalty - missing_prov_penalty, 4)


def run_compare(query: str, policies: list[str], args: argparse.Namespace) -> tuple[list[dict[str, Any]], Path]:
    out_dir = Path(args.output_root or DEFAULT_OUTPUT_ROOT) / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for policy in policies:
        packet, _ = run_preview(
            query=query,
            db_path=args.db,
            policy=policy,
            top_k=args.top_k,
            max_packet_chars=args.max_packet_chars,
            output_root=out_dir,
            save=False,
            require_provenance=args.require_provenance,
        )
        save_packet(packet, out_dir, suffix=f"_{policy}")
        metrics = to_dict(packet.metrics)
        metrics["packet_quality_score"] = packet_quality_score(metrics)
        rows.append({"policy": policy, "packet": to_dict(packet), "metrics": metrics})
    (out_dir / "comparison_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Memory Packet Policy Comparison", "", f"- Query: `{query}`", "", "| policy | chars | lines | evidence | kinds | dup_groups | compression | chars/evidence | provenance | latency_ms | quality |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        m = row["metrics"]
        lines.append(f"| {row['policy']} | {m['packet_chars']} | {m['packet_line_count']} | {m['evidence_count']} | {m['unique_kind_count']} | {m['duplicate_group_count']} | {m['compression_ratio']} | {m['chars_per_evidence']} | {m['provenance_line_rate']} | {m['latency_ms']} | {m['packet_quality_score']} |")
    if rows:
        lines += ["", "## Summary", ""]
        lines.append(f"- Most compact packet: `{min(rows, key=lambda r: r['metrics']['packet_chars'])['policy']}`")
        lines.append(f"- Most evidence-dense packet: `{min(rows, key=lambda r: r['metrics']['chars_per_evidence'])['policy']}`")
        lines.append(f"- Highest provenance packet: `{max(rows, key=lambda r: r['metrics']['provenance_line_rate'])['policy']}`")
        lines.append(f"- Most repetitive packet: `{max(rows, key=lambda r: r['metrics']['duplicate_group_count'])['policy']}`")
        lines.append(f"- Best balanced packet: `{max(rows, key=lambda r: r['metrics']['packet_quality_score'])['policy']}`")
    (out_dir / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows, out_dir


def run_ranking_diagnostics(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Path]:
    decision, candidates, _policy_doc = route_memory(args.query, args.db, args.policy, args.top_k, args.max_packet_chars, args.require_provenance)
    out_dir = DIAGNOSTIC_OUTPUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, candidate in enumerate(candidates[: int(args.top_k or 10)], start=1):
        ranking = candidate.ranking or {}
        rows.append({
            "rank": index,
            "memory_item_id": candidate.memory_item_id,
            "kind": candidate.kind,
            "source_family": candidate.source_family,
            "final_score": ranking.get("final_score", candidate.score),
            "matched_terms": ",".join(ranking.get("matched_terms", [])),
            "source_artifact_path": candidate.source_artifact_path,
            "text_short": candidate.text[:180],
            "ranking": ranking,
        })
    (out_dir / "ranking_results.json").write_text(json.dumps({"decision": to_dict(decision), "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = ["rank", "memory_item_id", "kind", "source_family", "final_score", "matched_terms", "source_artifact_path", "text_short"]
    with (out_dir / "ranking_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})
    lines = [
        "# Memory Ranking Diagnostics",
        "",
        f"- Query: `{args.query}`",
        f"- Task type: `{decision.task_type}`",
        f"- Policy: `{decision.selected_policy}`",
        "",
        "| rank | id | kind | source_family | final_score | matched_terms | source | text |",
        "|---:|---:|---|---|---:|---|---|---|",
    ]
    for row in rows:
        source = str(row.get("source_artifact_path") or "").replace("|", "/")
        text = str(row.get("text_short") or "").replace("|", "/")
        lines.append(f"| {row['rank']} | {row.get('memory_item_id') or ''} | {row.get('kind') or ''} | {row.get('source_family') or ''} | {row.get('final_score')} | {row.get('matched_terms') or ''} | {source} | {text} |")
    (out_dir / "ranking_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows, out_dir


def build_synthetic_memory(db_path: Path) -> None:
    store = MemoryStore(db_path)
    store.init_schema()
    ep = store.insert_episode(run_id="packet-selftest", task_text="packet self-test fixture", success=True, artifact_path=str(db_path), source_kind="packet_selftest")
    conn = store.connect()
    try:
        with conn:
            fixtures = [
                ("json_contamination_warning", "Qwen emitted <think> before JSON and validation failed for the tool call.", "synthetic://think-json-validation"),
                ("json_contamination_warning", "Qwen emitted <think> before JSON and validation failed for the tool call.", "synthetic://think-json-validation-2"),
                ("json_contamination_warning", "Qwen emitted <think> before JSON and validation failed for the tool call.", "synthetic://think-json-validation-3"),
                ("benchmark_result", "Qwen benchmark memory ctx=512 cache_k=f16 cache_v=f16 decode_tps=19.6 on RTX 4060.", "synthetic://qwen-ctx512"),
                ("policy_warning", "Absolute path policy sandbox violation: Windows drive paths are rejected; use sandbox-relative paths.", "synthetic://absolute-path-policy"),
                ("successful_pattern", "Successful calc write workflow used calc_eval then fs_write to save the result.", "synthetic://calc-write-workflow"),
            ]
            for kind, text, source in fixtures:
                store.insert_memory_item(conn, source_episode_id=ep, kind=kind, text=text, importance=0.9, confidence=0.95, status="active", source_artifact_path=source)
        vectorize_memory_items(db_path)
    finally:
        conn.close()


def self_test() -> int:
    failures = []
    out_root = DEFAULT_OUTPUT_ROOT / f"selftest_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    out_root.mkdir(parents=True, exist_ok=True)
    db = out_root / "synthetic_memory.sqlite3"
    build_synthetic_memory(db)
    for policy in ("none", "keyword_only", "vector_only", "hybrid_default", "failure_first", "benchmark", "safety_first", "recent_buffer"):
        try:
            load_policy(policy)
        except Exception as exc:
            failures.append(f"policy load failed {policy}: {exc}")
    checks = [
        ("json tool call failed because qwen emitted think tags", "failure_first", ["failure", "keyword", "vector"], ["think", "json", "validation"]),
        ("benchmark qwen 4060 ctx 512 decode_tps", "benchmark", ["benchmark", "keyword"], ["qwen", "ctx=512", "decode_tps"]),
        ("absolute path policy violation sandbox", "safety_first", ["safety", "keyword"], ["path", "policy", "sandbox"]),
        ("successful calc write workflow", "hybrid_default", ["hybrid", "keyword"], ["calc", "write"]),
    ]
    for query, policy, expected_experts, terms in checks:
        packet, _ = run_preview(query, db, policy, top_k=5, max_packet_chars=1200, output_root=out_root, save=True)
        blob = packet.packet_text.lower()
        if not all(expert in packet.routing_decision.selected_experts for expert in expected_experts):
            failures.append(f"experts missing for {policy}")
        if not all(term.lower() in blob for term in terms):
            failures.append(f"terms missing for {policy}: {terms}")
        if not packet.candidates_considered:
            failures.append(f"no candidates for {policy}")
        if packet.metrics.packet_chars > 1200:
            failures.append(f"packet too large for {policy}")
        if packet.packet_lines and packet.metrics.provenance_line_rate <= 0:
            failures.append(f"missing provenance for {policy}")
        repeated_text = len({c.text for c in packet.candidates_considered}) < len(packet.candidates_considered)
        if policy == "failure_first" and repeated_text:
            if packet.metrics.duplicate_group_count < 1:
                failures.append("failure_first did not group repeated think-tag memories")
            if packet.metrics.evidence_count <= packet.metrics.packet_line_count:
                failures.append("failure_first grouping did not preserve multiple evidence items")
            if packet.metrics.packet_line_count >= packet.metrics.raw_candidate_count:
                failures.append("failure_first packet line count was not compressed")
    none_packet, _ = run_preview("anything", db, "none", top_k=5, output_root=out_root, save=True)
    if none_packet.metrics.packet_line_count != 0:
        failures.append("none policy returned packet lines")
    rows, compare_dir = run_compare("json tool call failed because qwen emitted think tags", ["keyword_only", "vector_only", "hybrid_default", "failure_first"], argparse.Namespace(db=str(db), top_k=5, max_packet_chars=1200, output_root=str(out_root), require_provenance=False))
    if len(rows) != 4 or not (compare_dir / "comparison_results.json").exists():
        failures.append("compare command failed")
    if "chars_per_evidence" not in rows[0]["metrics"]:
        failures.append("compare output missing quality metrics")
    report_paths = list(out_root.rglob("packet_report*.md"))
    if not report_paths or "Grouped Evidence" not in report_paths[0].read_text(encoding="utf-8"):
        failures.append("packet report missing grouped evidence table")
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
    parser = argparse.ArgumentParser(description="Preview read-only IVY memory packets.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parent.add_argument("--policy", default=None)
    parent.add_argument("--top-k", type=int, default=None)
    parent.add_argument("--max-packet-chars", type=int, default=None)
    parent.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parent.add_argument("--json", action="store_true")
    parent.add_argument("--no-save", action="store_true")
    parent.add_argument("--require-provenance", action="store_true")
    parent.add_argument("--include-candidates", action="store_true")

    p_preview = sub.add_parser("preview", parents=[parent])
    p_preview.add_argument("--query", required=True)

    p_compare = sub.add_parser("compare", parents=[parent])
    p_compare.add_argument("--query", required=True)
    p_compare.add_argument("--policies", nargs="+", required=True)

    p_diag = sub.add_parser("diagnose-ranking", parents=[parent])
    p_diag.add_argument("--query", required=True)

    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.cmd == "self-test":
        raise SystemExit(self_test())
    if args.cmd == "preview":
        packet, out_dir = run_preview(args.query, args.db, args.policy, args.top_k, args.max_packet_chars, args.output_root, not args.no_save, args.require_provenance)
        if args.json:
            payload = to_dict(packet)
            if not args.include_candidates:
                payload.pop("candidates_considered", None)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(packet.packet_text)
            if out_dir:
                print(f"\nSaved packet preview: {out_dir}")
    elif args.cmd == "compare":
        rows, out_dir = run_compare(args.query, args.policies, args)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print(f"Saved comparison: {out_dir}")
    elif args.cmd == "diagnose-ranking":
        rows, out_dir = run_ranking_diagnostics(args)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print(f"task_type: {classify_task(args.query)}")
            print(f"policy: {args.policy}")
            for row in rows:
                print(f"{row['rank']}. id={row.get('memory_item_id')} kind={row.get('kind')} family={row.get('source_family')} score={row.get('final_score')} terms={row.get('matched_terms')}")
                print(f"   source={row.get('source_artifact_path')}")
                print(f"   {row.get('text_short')}")
            print(f"Saved ranking diagnostics: {out_dir}")


if __name__ == "__main__":
    main()
