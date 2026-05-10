from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from generate_ivy_real_dataset import (
        AUTHORITIES,
        CATEGORIES,
        ROOT,
        SOURCE_FAMILIES,
        STALENESS,
        build_cases,
        build_items,
        case,
        item,
        rough_tokens,
        sha256_file,
    )
except ModuleNotFoundError:
    from scripts.generate_ivy_real_dataset import (
        AUTHORITIES,
        CATEGORIES,
        ROOT,
        SOURCE_FAMILIES,
        STALENESS,
        build_cases,
        build_items,
        case,
        item,
        rough_tokens,
        sha256_file,
    )


def extra_items() -> list[dict[str, Any]]:
    return [
        item(
            "cp7_ivy_real_mini_status",
            "doc_memory",
            "high",
            "current",
            ["cp7", "ivy_real", "dataset"],
            "CP7 added the Ivy-real mini dataset with 37 hand-curated IVY evidence items and 30 labeled cases across all 10 benchmark categories.",
            "docs/CP7_CP9_STATUS_2026-05-10.md",
            claim_type="metric",
            canonical_for=["cp7_status"],
        ),
        item(
            "cp8_indexed_backend_status",
            "doc_memory",
            "high",
            "current",
            ["cp8", "indexed", "candidate_backend"],
            "CP8 added the indexed Python candidate backend. It builds postings, family indexes, ID maps, and conflict neighbors while leaving final scoring, gates, route proofs, and frontier packets in Python.",
            "docs/CP7_CP9_STATUS_2026-05-10.md",
            canonical_for=["cp8_status"],
        ),
        item(
            "cp8_stress_latency_result",
            "benchmark_artifact",
            "high",
            "current",
            ["cp8", "stress", "latency"],
            "On the stress dataset, CP8 indexed backend preserved 62/62 quality and reduced mean latency from 307.263 ms scan to 124.441 ms indexed, about a 2.47x speedup.",
            "docs/CP7_CP9_STATUS_2026-05-10.md",
            claim_type="metric",
            canonical_for=["cp8_stress_speedup"],
        ),
        item(
            "cp9_rust_probe_status",
            "benchmark_artifact",
            "high",
            "current",
            ["cp9", "rust", "candidate_recall"],
            "CP9 Rust probe reached required recall@32 of 1.0 on Ivy-real and stress, with failed_cases equal to 0 for both probe runs.",
            "docs/CP7_CP9_STATUS_2026-05-10.md",
            claim_type="metric",
            canonical_for=["cp9_probe_recall"],
        ),
        item(
            "cp9_direct_backend_overhead",
            "debug_failure",
            "high",
            "current",
            ["cp9", "rust", "overhead", "process_spawn"],
            "The direct Rust backend is functionally integrated, but the current Python adapter shells out per query and the Rust binary reloads the corpus and rebuilds the index each run. The next optimization is a batch or persistent Rust process.",
            "docs/AUTORESEARCH_TRACK_RECORD_2026-05-10.md",
            claim_type="failure_mode",
            canonical_for=["cp9_rust_overhead"],
        ),
        item(
            "kittylitter_path_wrapper",
            "runbook",
            "high",
            "current",
            ["kittylitter", "wrapper", "codex_app_server"],
            "The kittylitter PATH wrapper exposes start, status, stop, restart, logs, and foreground commands for the Codex app-server at ws://127.0.0.1:8390.",
            "root/HANDOFF_CONTEXT.md",
            claim_type="command",
            canonical_for=["kittylitter_wrapper"],
        ),
        item(
            "litter_tailscale_ssh_connection",
            "runbook",
            "high",
            "current",
            ["litter", "tailscale", "ssh"],
            "Phone-side Litter can reach this PC over Tailscale at host 100.69.245.47 or MagicDNS ari-legion.taild0cc8e.ts.net with user arahe on port 22.",
            "root/HANDOFF_CONTEXT.md",
            claim_type="procedure",
            canonical_for=["litter_tailscale_connection"],
        ),
        item(
            "signal_ping_token_runtime_note",
            "debug_failure",
            "medium",
            "current",
            ["signal", "ping", "token"],
            "Signal pings may fail with HTTP 401 when the default dev-token is stale. Inspect the running signal-daemon command line or admin token file before retrying with the active token.",
            "docs/AUTORESEARCH_TRACK_RECORD_2026-05-10.md",
            claim_type="failure_mode",
            canonical_for=["signal_ping_401"],
        ),
    ]


def variant_cases(base_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    retrieve_templates = [
        "{query}",
        "Current IVY check: {query}",
        "Authoritative record check: {query}",
        "Compact packet question: {query}",
    ]
    abstain_templates = [
        "{query}",
    ]
    for base in base_cases:
        templates = abstain_templates if base.get("must_abstain") or not base.get("required_source_ids") else retrieve_templates
        for idx, template in enumerate(templates, start=1):
            cloned = dict(base)
            cloned["id"] = f"v2_{idx:02d}_{base['id']}"
            cloned["query"] = template.format(query=base["query"])
            cloned["notes"] = "Ivy-real v2 deterministic query variant. " + str(base.get("notes", ""))
            rows.append(cloned)
    return rows


def extra_cases() -> list[dict[str, Any]]:
    return [
        case("v2_cp7_status", "benchmark", "How many cases and evidence items did CP7 Ivy-real mini add?", ["cp7_ivy_real_mini_status"]),
        case("v2_cp8_status", "local_codebase", "What did the CP8 indexed Python backend change and what stayed in Python?", ["cp8_indexed_backend_status"]),
        case("v2_cp8_speedup", "benchmark", "What was the CP8 stress latency speedup from scan to indexed?", ["cp8_stress_latency_result"]),
        case("v2_cp9_probe", "benchmark", "What did the CP9 Rust probe show for required recall at top 32?", ["cp9_rust_probe_status"]),
        case("v2_cp9_overhead", "debug", "Why is the current direct Rust backend still not cheap enough?", ["cp9_direct_backend_overhead"]),
        case("v2_kittylitter_wrapper", "exact_command", "What commands does the kittylitter wrapper expose for the Codex app server?", ["kittylitter_path_wrapper"]),
        case("v2_litter_connection", "workflow", "How should the phone Litter app connect to this PC over Tailscale SSH?", ["litter_tailscale_ssh_connection"]),
        case("v2_signal_401", "debug", "What should we check when Signal pings return HTTP 401 unauthorized?", ["signal_ping_token_runtime_note"]),
    ]


def build_v2_items() -> list[dict[str, Any]]:
    seen = set()
    rows = []
    for row in [*build_items(), *extra_items()]:
        if row["id"] in seen:
            raise ValueError(f"duplicate item id: {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    return rows


def build_v2_cases() -> list[dict[str, Any]]:
    seen = set()
    rows = [*variant_cases(build_cases()), *extra_cases()]
    for row in rows:
        if row["id"] in seen:
            raise ValueError(f"duplicate case id: {row['id']}")
        seen.add(row["id"])
    return rows


def write_dataset(out_dir: Path, *, seed: int) -> None:
    items = build_v2_items()
    cases = build_v2_cases()
    corpus_dir = out_dir / "corpus"
    eval_dir = out_dir / "eval"
    metadata_dir = out_dir / "metadata"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = corpus_dir / "corpus_items.jsonl"
    cases_path = eval_dir / "cases.json"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in items:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    cases_path.write_text(
        json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    family_counts = Counter(row["source_family"] for row in items)
    authority_counts = Counter(row["authority"] for row in items)
    staleness_counts = Counter(row["staleness"] for row in items)
    category_counts = Counter(row["category"] for row in cases)
    manifest = {
        "schema_version": "context_stress_manifest.v0.2",
        "dataset_id": f"context_stress_ivy_real_{seed}",
        "scale": "ivy_real",
        "seed": seed,
        "created_at": datetime(2026, 5, 10, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "token_target": 1,
        "estimated_tokens": sum(rough_tokens(row["text"]) for row in items),
        "token_target_met": True,
        "item_count": len(items),
        "case_count": len(cases),
        "source_family_counts": {key: family_counts[key] for key in SOURCE_FAMILIES},
        "authority_counts": {key: authority_counts[key] for key in AUTHORITIES},
        "staleness_counts": {key: staleness_counts[key] for key in STALENESS},
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "template_stats": {
            "template_files": {"hand_labeled_ivy_real_v1": len(build_items()), "ivy_real_v2_extra": len(extra_items())},
            "record_keys": {row["id"]: 1 for row in items},
            "warnings": [],
        },
        "files": {
            "corpus": "corpus/corpus_items.jsonl",
            "cases": "eval/cases.json",
            "manifest": "metadata/dataset_manifest.json",
        },
        "file_sha256": {
            "corpus": sha256_file(corpus_path),
            "cases": sha256_file(cases_path),
        },
        "generator": {
            "script": "scripts/generate_ivy_real_v2_dataset.py",
            "rough_tokenizer": "whitespace_split_v1",
            "deterministic": True,
        },
        "schema_ids": {
            "corpus_item": "context_stress.corpus_item.v0.2",
            "eval_case": "context_stress.eval_case.v0.2",
            "dataset_manifest": "context_stress.dataset_manifest.v0.2",
        },
        "generation": {
            "type": "hand_labeled_ivy_real_v2_augmented",
            "base_cases": len(build_cases()),
            "case_variants": len(cases) - len(extra_cases()),
            "extra_cases": len(extra_cases()),
            "notes": "V2 expands real IVY coverage with deterministic query variants plus current CP9, Litter, and Signal operational records.",
        },
    }
    (metadata_dir / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the expanded Ivy-real v2 dataset.")
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "context_stress_ivy_real_v2")
    parser.add_argument("--seed", type=int, default=778)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    write_dataset(output, seed=args.seed)
    print(json.dumps({"output": str(output), "items": len(build_v2_items()), "cases": len(build_v2_cases())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
