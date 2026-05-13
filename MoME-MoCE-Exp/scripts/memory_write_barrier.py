from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_FAMILIES = {
    "benchmark_artifact",
    "debug_failure",
    "doc_memory",
    "runbook",
    "safety_policy",
    "source_code",
    "user_note",
    "workflow_trace",
}
ALLOWED_AUTHORITY = {"high", "medium", "low", "decoy"}
ALLOWED_STALENESS = {"current", "stale", "unknown", "decoy"}
ALLOWED_SAFETY_LABELS = {"normal", "safety_critical", "unsafe_decoy"}
ALLOWED_EXPOSURE = {"frontier_ok", "contrastive_ok", "metadata_only"}

DRIVE_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
SECRET_RE = re.compile(r"\b(api[_ -]?key|password|private[_ -]?key|secret|token)\b", re.I)


class MemoryWriteError(ValueError):
    pass


def _as_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise MemoryWriteError(f"{field} must be a non-empty list of strings")
    return [item.strip() for item in value]


def _clean_source_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryWriteError("source_path must be a non-empty relative path")
    source_path = value.replace("\\", "/").strip()
    if source_path.startswith("/") or DRIVE_PATH_RE.match(source_path):
        raise MemoryWriteError("source_path must not be absolute")
    parts = [part for part in source_path.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise MemoryWriteError("source_path must not contain traversal segments")
    if not parts:
        raise MemoryWriteError("source_path must contain at least one path segment")
    return "/".join(parts)


def _require_enum(record: dict[str, Any], field: str, allowed: set[str]) -> str:
    value = record.get(field)
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise MemoryWriteError(f"{field} must be one of: {choices}")
    return value


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_memory_id(text: str, source_path: str) -> str:
    digest = hashlib.sha256((source_path + "\n" + text).encode("utf-8")).hexdigest()
    return "mem_" + digest[:16]


def validate_memory_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise MemoryWriteError("record must be a JSON object")
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        raise MemoryWriteError("text must be a non-empty string")

    source_family = _require_enum(record, "source_family", ALLOWED_SOURCE_FAMILIES)
    authority = _require_enum(record, "authority", ALLOWED_AUTHORITY)
    staleness = _require_enum(record, "staleness", ALLOWED_STALENESS)
    safety_label = _require_enum(record, "safety_label", ALLOWED_SAFETY_LABELS)
    exposure_policy = _require_enum(record, "exposure_policy", ALLOWED_EXPOSURE)
    taint_labels = _as_string_list(record.get("taint_labels"), "taint_labels")
    source_path = _clean_source_path(record.get("source_path"))

    if exposure_policy == "frontier_ok" and SECRET_RE.search(text):
        raise MemoryWriteError("frontier_ok memory text must not contain obvious secret material")
    if any(label in {"private", "secret", "credential"} for label in taint_labels):
        raise MemoryWriteError("private or credential-tainted memory is not admissible")
    if authority == "decoy" and exposure_policy != "contrastive_ok":
        raise MemoryWriteError("decoy authority records must use contrastive_ok exposure")
    if staleness == "decoy" and authority != "decoy":
        raise MemoryWriteError("decoy staleness must use decoy authority")
    if safety_label == "unsafe_decoy" and exposure_policy != "contrastive_ok":
        raise MemoryWriteError("unsafe_decoy records must use contrastive_ok exposure")

    normalized = {
        "id": record.get("id") or canonical_memory_id(text.strip(), source_path),
        "text": text.strip(),
        "source_family": source_family,
        "authority": authority,
        "staleness": staleness,
        "source_path": source_path,
        "safety_label": safety_label,
        "taint_labels": taint_labels,
        "exposure_policy": exposure_policy,
        "content_sha256": content_sha256(text.strip()),
        "created_at": record.get("created_at") or datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if not isinstance(normalized["id"], str) or not normalized["id"].strip():
        raise MemoryWriteError("id must be a non-empty string when supplied")
    normalized["id"] = normalized["id"].strip()
    return normalized


def append_memory_record(jsonl_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_memory_record(record)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(normalized, sort_keys=True) + "\n")
    return normalized


def _load_record(path: Path | None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig") if path else input().lstrip("\ufeff")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise MemoryWriteError("input JSON must be an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or append MoME/MoCE memory records.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", type=Path)

    append = sub.add_parser("append")
    append.add_argument("--input", type=Path)
    append.add_argument("--jsonl", type=Path, required=True)

    args = parser.parse_args()
    record = _load_record(args.input)
    if args.command == "validate":
        print(json.dumps(validate_memory_record(record), indent=2))
    else:
        print(json.dumps(append_memory_record(args.jsonl, record), indent=2))


if __name__ == "__main__":
    main()
