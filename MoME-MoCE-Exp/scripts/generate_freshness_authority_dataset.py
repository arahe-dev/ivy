from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "context_stress_freshness_authority_cp27"


ITEMS: list[dict[str, Any]] = [
    {
        "id": "cp27_recall_cloud_current_price",
        "text": "Current Recall Cloud production pricing as of 2026-05-10 is USD $19 per month for the individual hosted sync plan.",
        "tags": ["recall", "recall cloud", "pricing", "production price", "current"],
        "source_family": "doc_memory",
        "authority": "high",
        "staleness": "current",
        "safety_label": "normal",
        "claim_type": "metric",
        "canonical_for": ["cp27_recall_cloud_current_price"],
        "conflicts_with": ["cp27_recall_cloud_stale_price"],
        "supersedes": ["cp27_recall_cloud_stale_price"],
        "created_at": "2026-05-10",
        "valid_from": "2026-05-10",
        "exposure_policy": "frontier_ok",
        "taint_labels": ["normal"],
    },
    {
        "id": "cp27_recall_cloud_stale_price",
        "text": "Old pricing draft from 2026-04-01 claimed Recall Cloud would cost USD $9 per month.",
        "tags": ["recall", "recall cloud", "pricing", "stale"],
        "source_family": "doc_memory",
        "authority": "low",
        "staleness": "stale",
        "safety_label": "normal",
        "claim_type": "metric",
        "canonical_for": [],
        "conflicts_with": ["cp27_recall_cloud_current_price"],
        "supersedes": [],
        "created_at": "2026-04-01",
        "valid_from": "2026-04-01",
        "valid_until": "2026-05-09",
        "exposure_policy": "frontier_ok",
        "taint_labels": ["normal"],
    },
    {
        "id": "cp27_signal_current_release_status",
        "text": "Current Signal production release status as of 2026-05-11 is internal beta; it is not public GA.",
        "tags": ["signal", "release status", "production status", "current", "beta"],
        "source_family": "doc_memory",
        "authority": "high",
        "staleness": "current",
        "safety_label": "normal",
        "claim_type": "fact",
        "canonical_for": ["cp27_signal_current_release_status"],
        "conflicts_with": ["cp27_signal_stale_ga_status"],
        "supersedes": ["cp27_signal_stale_ga_status"],
        "created_at": "2026-05-11",
        "valid_from": "2026-05-11",
        "exposure_policy": "frontier_ok",
        "taint_labels": ["normal"],
    },
    {
        "id": "cp27_signal_stale_ga_status",
        "text": "Old stale Signal note from 2026-04-15 said Signal was ready for public GA.",
        "tags": ["signal", "release status", "public ga", "stale"],
        "source_family": "doc_memory",
        "authority": "low",
        "staleness": "stale",
        "safety_label": "normal",
        "claim_type": "fact",
        "canonical_for": [],
        "conflicts_with": ["cp27_signal_current_release_status"],
        "supersedes": [],
        "created_at": "2026-04-15",
        "valid_from": "2026-04-15",
        "valid_until": "2026-05-10",
        "exposure_policy": "frontier_ok",
        "taint_labels": ["normal"],
    },
    {
        "id": "cp27_recall_cloud_identity_no_price",
        "text": "Recall Cloud is the hosted sync concept for Recall Board, but this identity note does not state any production price.",
        "tags": ["recall", "recall cloud", "identity"],
        "source_family": "doc_memory",
        "authority": "high",
        "staleness": "current",
        "safety_label": "normal",
        "claim_type": "fact",
        "canonical_for": [],
        "conflicts_with": [],
        "supersedes": [],
        "created_at": "2026-05-11",
        "valid_from": "2026-05-11",
        "exposure_policy": "frontier_ok",
        "taint_labels": ["normal"],
    },
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CP27 freshness/authority dataset.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    out = args.output if args.output.is_absolute() else (ROOT / args.output)
    corpus = out / "corpus" / "corpus_items.jsonl"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    with corpus.open("w", encoding="utf-8") as f:
        for item in ITEMS:
            record = {
                **item,
                "provenance": {
                    "artifact_path": f"docs/cp27/{item['id']}.md",
                    "record_key": item["id"],
                    "generator": "generate_freshness_authority_dataset.py",
                },
            }
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(out / "metadata" / "dataset_manifest.json", {"items": len(ITEMS), "dataset": "context_stress_freshness_authority_cp27"})
    write_json(out / "eval" / "cases.json", {"cases": []})
    print(json.dumps({"output": str(out), "items": len(ITEMS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
