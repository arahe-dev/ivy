from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .memory_store import DEFAULT_DB_PATH, MemoryStore


REPO_ROOT = Path(__file__).resolve().parents[1]
MOME_MOCE_SCRIPTS = REPO_ROOT / "MoME-MoCE-Exp" / "scripts"

import sys

if str(MOME_MOCE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(MOME_MOCE_SCRIPTS))

from memory_write_barrier import MemoryWriteError, validate_memory_record  # noqa: E402


DEFAULT_EXPORT_DIR = REPO_ROOT / "runs" / "acca_runtime_corpus"


def _rel_source_path(value: str | None) -> str:
    if not value:
        return "ivy_agent_demo/memory/ivy_memory.sqlite3"
    path_text = str(value).replace("\\", "/")
    root = str(REPO_ROOT).replace("\\", "/").rstrip("/") + "/"
    if path_text.lower().startswith(root.lower()):
        return path_text[len(root) :]
    drive_match = re.match(r"^[A-Za-z]:/(.*)$", path_text)
    if drive_match:
        return "external/" + drive_match.group(1).lstrip("/")
    if path_text.startswith("/"):
        return "external/" + path_text.lstrip("/")
    return path_text


def _source_family(kind: str) -> str:
    if kind == "benchmark_result":
        return "benchmark_artifact"
    if kind in {"policy_warning", "validation_warning"}:
        return "safety_policy"
    if kind in {"failure_warning", "json_contamination_warning"}:
        return "debug_failure"
    if kind == "runbook_command":
        return "runbook"
    if kind == "successful_pattern":
        return "workflow_trace"
    return "user_note"


def _authority(confidence: float | None, kind: str) -> str:
    if kind in {"policy_warning", "validation_warning"}:
        return "high"
    if confidence is not None and confidence >= 0.9:
        return "high"
    if confidence is not None and confidence >= 0.65:
        return "medium"
    return "low"


def _safety_label(kind: str, text: str) -> str:
    blob = f"{kind} {text}".lower()
    if any(term in blob for term in ["policy", "sandbox", "blocked", "absolute path", "secret"]):
        return "safety_critical"
    return "normal"


def _tags(kind: str, text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9_]+", f"{kind} {text}".lower())
    counts = Counter(tokens)
    preferred = [token for token, _ in counts.most_common(12) if len(token) > 2]
    return list(dict.fromkeys([kind] + preferred))[:12]


def _corpus_id(memory_id: int, text: str) -> str:
    digest = hashlib.sha256(f"{memory_id}\n{text}".encode("utf-8")).hexdigest()
    return f"runtime_memory_{memory_id}_{digest[:10]}"


def row_to_corpus_item(row: Any) -> dict[str, Any]:
    kind = str(row["kind"] or "memory_item")
    text = str(row["text"])
    source_path = _rel_source_path(row["source_artifact_path"])
    barrier_record = {
        "text": text,
        "source_family": _source_family(kind),
        "authority": _authority(row["confidence"], kind),
        "staleness": "current" if str(row["status"] or "active") == "active" else "stale",
        "source_path": source_path,
        "safety_label": _safety_label(kind, text),
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
    }
    normalized = validate_memory_record(barrier_record)
    return {
        "id": _corpus_id(int(row["id"]), text),
        "source_family": normalized["source_family"],
        "authority": normalized["authority"],
        "staleness": normalized["staleness"],
        "safety_label": normalized["safety_label"],
        "claim_type": kind,
        "tags": _tags(kind, text),
        "text": normalized["text"],
        "provenance": {
            "artifact_path": normalized["source_path"],
            "memory_item_id": int(row["id"]),
            "source_episode_id": row["source_episode_id"],
            "created_at": row["created_at"],
            "content_sha256": normalized["content_sha256"],
        },
        "conflicts_with": [],
        "supersedes": [],
        "canonical_for": [kind],
        "exposure_policy": normalized["exposure_policy"],
        "taint_labels": normalized["taint_labels"],
    }


def export_acca_corpus(db_path: Path = DEFAULT_DB_PATH, output_dir: Path = DEFAULT_EXPORT_DIR) -> dict[str, Any]:
    store = MemoryStore(db_path)
    store.init_schema()
    output_dir = output_dir.resolve()
    corpus_dir = output_dir / "corpus"
    metadata_dir = output_dir / "metadata"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = corpus_dir / "corpus_items.jsonl"

    conn = store.connect()
    try:
        rows = conn.execute(
            """
            SELECT id, source_episode_id, kind, text, importance, confidence, status,
                   source_artifact_path, created_at, last_used_at
            FROM memory_items
            WHERE status IS NULL OR status != 'rejected'
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    items: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        try:
            items.append(row_to_corpus_item(row))
        except MemoryWriteError as exc:
            rejected.append(
                {
                    "memory_item_id": int(row["id"]),
                    "kind": row["kind"],
                    "source_artifact_path": row["source_artifact_path"],
                    "reason": str(exc),
                }
            )
    with corpus_path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    if rejected:
        with (metadata_dir / "rejected_memory_items.jsonl").open("w", encoding="utf-8") as handle:
            for item in rejected:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

    manifest = {
        "dataset_id": "ivy_runtime_acca_export",
        "source_db": str(Path(db_path).resolve()),
        "output_dir": str(output_dir),
        "corpus_items": len(items),
        "rejected_items": len(rejected),
        "source_family_counts": dict(Counter(item["source_family"] for item in items)),
    }
    (metadata_dir / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Export IVY SQLite memory into ACCA corpus JSONL.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    args = parser.parse_args()
    print(json.dumps(export_acca_corpus(args.db, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
