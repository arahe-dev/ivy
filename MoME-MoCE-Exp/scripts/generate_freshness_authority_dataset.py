from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from generate_ivy_real_dataset import CATEGORIES, sha256_file
except ModuleNotFoundError:
    from scripts.generate_ivy_real_dataset import CATEGORIES, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def item(
    item_id: str,
    *,
    source_family: str,
    authority: str,
    staleness: str,
    tags: list[str],
    text: str,
    artifact_path: str,
    created_at: str,
    valid_from: str | None = None,
    valid_until: str | None = None,
    conflicts_with: list[str] | None = None,
    supersedes: list[str] | None = None,
    safety_label: str = "normal",
    claim_type: str = "fact",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": item_id,
        "source_family": source_family,
        "authority": authority,
        "created_at": created_at,
        "supersedes": supersedes or [],
        "tags": tags,
        "text": text,
        "provenance": {
            "artifact_path": artifact_path,
            "source_hash": "cp27_generated",
            "record_key": item_id,
            "generator": "scripts/generate_freshness_authority_dataset.py",
        },
        "staleness": staleness,
        "conflicts_with": conflicts_with or [],
        "safety_label": safety_label,
        "taint_labels": ["normal"] if safety_label == "normal" else [safety_label],
        "exposure_policy": "frontier_ok",
        "claim_type": claim_type,
        "canonical_for": [item_id],
    }
    if valid_from:
        row["valid_from"] = valid_from
    if valid_until:
        row["valid_until"] = valid_until
    return row


CORPUS_ITEMS = [
    item(
        "cp27_recall_cloud_current_price",
        source_family="doc_memory",
        authority="high",
        staleness="current",
        tags=["recall", "recall cloud", "pricing", "production price", "current"],
        text="Current Recall Cloud production pricing as of 2026-05-10 is USD $19 per month for the individual hosted sync plan.",
        artifact_path="docs/cp27/recall_cloud_pricing_2026_05_10.md",
        created_at="2026-05-10",
        valid_from="2026-05-10",
        conflicts_with=["cp27_recall_cloud_stale_price"],
        supersedes=["cp27_recall_cloud_stale_price"],
        claim_type="metric",
    ),
    item(
        "cp27_recall_cloud_stale_price",
        source_family="doc_memory",
        authority="low",
        staleness="stale",
        tags=["recall", "recall cloud", "pricing", "stale"],
        text="Old pricing draft from 2026-04-01 claimed Recall Cloud would cost USD $9 per month.",
        artifact_path="docs/cp27/recall_cloud_pricing_2026_04_01.md",
        created_at="2026-04-01",
        valid_from="2026-04-01",
        valid_until="2026-05-09",
        conflicts_with=["cp27_recall_cloud_current_price"],
        claim_type="metric",
    ),
    item(
        "cp27_signal_current_release_status",
        source_family="doc_memory",
        authority="high",
        staleness="current",
        tags=["signal", "release status", "production status", "current", "beta"],
        text="Current Signal production release status as of 2026-05-11 is internal beta; it is not public GA.",
        artifact_path="docs/cp27/signal_release_status_2026_05_11.md",
        created_at="2026-05-11",
        valid_from="2026-05-11",
        conflicts_with=["cp27_signal_stale_ga_status"],
        supersedes=["cp27_signal_stale_ga_status"],
        claim_type="fact",
    ),
    item(
        "cp27_signal_stale_ga_status",
        source_family="doc_memory",
        authority="low",
        staleness="stale",
        tags=["signal", "release status", "public ga", "stale"],
        text="Old stale Signal note from 2026-04-15 said Signal was ready for public GA.",
        artifact_path="docs/cp27/signal_release_status_2026_04_15.md",
        created_at="2026-04-15",
        valid_from="2026-04-15",
        valid_until="2026-05-10",
        conflicts_with=["cp27_signal_current_release_status"],
        claim_type="fact",
    ),
    item(
        "cp27_recall_cloud_identity_no_price",
        source_family="doc_memory",
        authority="high",
        staleness="current",
        tags=["recall", "recall cloud", "identity"],
        text="Recall Cloud is the hosted sync concept for Recall Board, but this identity note does not state any production price.",
        artifact_path="docs/cp27/recall_cloud_identity.md",
        created_at="2026-05-11",
        valid_from="2026-05-11",
    ),
]


CASES = [
    {
        "id": "cp27_current_recall_cloud_price",
        "category": "stale_conflict",
        "query": "What is the latest production price for Recall Cloud?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["cp27_recall_cloud_current_price"],
        "forbidden_source_ids": ["cp27_recall_cloud_stale_price", "cp27_recall_cloud_identity_no_price"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": True,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "compare_current_vs_stale",
        "notes": "Current dated pricing evidence should beat stale pricing and non-pricing identity notes.",
    },
    {
        "id": "cp27_current_signal_release_status",
        "category": "stale_conflict",
        "query": "What is the current production release status or GA status for Signal?",
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": ["cp27_signal_current_release_status"],
        "forbidden_source_ids": ["cp27_signal_stale_ga_status"],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": True,
        "requires_safety_priority": False,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "compare_current_vs_stale",
        "notes": "Current release status needs dated current evidence.",
    },
    {
        "id": "cp27_unsupported_nebula_cloud_price",
        "category": "unanswerable",
        "query": "What is the latest production price for Nebula Cloud?",
        "should_retrieve": False,
        "retrieval_ratio_target": [0.0, 0.01],
        "required_source_ids": [],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": True,
        "requires_conflict_resolution": False,
        "requires_safety_priority": False,
        "provenance_required": False,
        "max_evidence_items": 0,
        "answer_contract": "abstain",
        "notes": "No dated authoritative Nebula Cloud pricing evidence exists.",
    },
]


def write_dataset(output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    (output / "corpus").mkdir(parents=True)
    (output / "eval").mkdir(parents=True)
    (output / "metadata").mkdir(parents=True)
    corpus_path = output / "corpus" / "corpus_items.jsonl"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in CORPUS_ITEMS:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    cases_path = output / "eval" / "cases.json"
    cases_path.write_text(json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": CASES}, ensure_ascii=False, indent=2), encoding="utf-8")
    category_counts = Counter(case["category"] for case in CASES)
    manifest = {
        "schema_version": "context_stress_dataset_manifest.v0.1",
        "dataset_id": "context_stress_freshness_authority_cp27",
        "created_at": datetime(2026, 5, 11, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_count": len(CASES),
        "corpus_items": len(CORPUS_ITEMS),
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "file_sha256": {
            "corpus": sha256_file(corpus_path),
            "cases": sha256_file(cases_path),
        },
        "generator": {
            "script": "scripts/generate_freshness_authority_dataset.py",
            "deterministic": True,
        },
        "generation": {
            "type": "cp27_freshness_version_authority",
            "notes": "Tests current commercial/release claims against stale claims and related non-answering notes.",
        },
    }
    (output / "metadata" / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output), **manifest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CP27 freshness/version authority dataset.")
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "context_stress_freshness_authority_cp27")
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = write_dataset(output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
