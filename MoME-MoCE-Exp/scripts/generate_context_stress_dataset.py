from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
TOKEN_TARGETS = {"smoke": 50_000, "medium": 200_000, "stress": 2_000_000}
DETERMINISTIC_CREATED_AT = "2026-05-09T00:00:00Z"

# Known list-bearing keys across the current templates plus older/newer fixture
# shapes. Unknown list-of-dict keys are also consumed as template records below.
KNOWN_TEMPLATE_LIST_KEYS = {
    "templates",
    "records",
    "policy_records",
    "override_attempts",
    "json_failure_patterns",
    "tool_traces",
    "tool_debug_failures",
    "debug_failures",
    "debug_log_patterns",
    "distractors",
}

FAMILY_BY_KEY = {
    "templates": None,
    "records": "benchmark_artifact",
    "policy_records": "safety_policy",
    "override_attempts": "safety_policy",
    "json_failure_patterns": "debug_failure",
    "tool_traces": "workflow_trace",
    "tool_debug_failures": "debug_failure",
    "debug_failures": "debug_failure",
    "debug_log_patterns": "debug_failure",
    "distractors": "distractor",
}


class TemplateLoadError(ValueError):
    pass


def rough_tokens(text: str) -> int:
    """Cheap deterministic token proxy shared with the validator."""
    return max(1, len(str(text).split()))


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_id(value: Any, *, fallback: str) -> str:
    if value is None or str(value).strip() == "":
        value = fallback
    out = str(value).strip().replace("-", "_").replace(" ", "_")
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in out).lower()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def sorted_unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted({str(v) for v in values if v is not None and str(v) != ""})


def infer_family(key: str, record: dict[str, Any], file_family: Any) -> str:
    explicit = record.get("source_family") or file_family
    if explicit:
        return str(explicit)
    mapped = FAMILY_BY_KEY.get(key)
    if mapped:
        return mapped
    haystack = f"{key} {stable_json(record)}".lower()
    if "decoy" in haystack or "distractor" in haystack:
        return "distractor"
    if "safety" in haystack or "policy" in haystack or "override" in haystack:
        return "safety_policy"
    if "trace" in haystack or "workflow" in haystack or "tool_" in haystack:
        return "workflow_trace"
    if "debug" in haystack or "json" in haystack or "error" in haystack:
        return "debug_failure"
    return "benchmark_artifact"


def infer_authority(record: dict[str, Any], family: str) -> str:
    if record.get("authority"):
        return str(record["authority"])
    haystack = stable_json(record).lower()
    if family == "distractor" or record.get("safety_label") == "unsafe_decoy" or record.get("staleness") == "decoy":
        return "decoy"
    if "stale" in haystack or "superseded" in haystack or record.get("superseded_by"):
        return "low"
    severity = str(record.get("severity", "")).upper()
    if severity in {"HIGH", "CRITICAL"} or "latest" in haystack or "current" in haystack:
        return "high"
    return "medium"


def extract_text(record: dict[str, Any]) -> str:
    for key in ("text", "content", "body", "markdown"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if "content_template" in record:
        value = record["content_template"]
    else:
        # Avoid duplicating generated metadata in the primary text when a record is
        # already in normalized corpus-item shape.
        value = {k: v for k, v in record.items() if k not in {"id", "template_id", "source_family", "authority", "tags"}}
    return stable_json(value)


def iter_template_records(path: Path, data: dict[str, Any]) -> Iterable[tuple[str, int, dict[str, Any]]]:
    consumed_keys: set[str] = set()
    for key in sorted(KNOWN_TEMPLATE_LIST_KEYS):
        value = data.get(key)
        if isinstance(value, list):
            consumed_keys.add(key)
            for index, record in enumerate(value):
                if isinstance(record, dict):
                    yield key, index, record
                else:
                    yield key, index, {"content_template": record}

    # Forward compatibility: consume additional top-level list-of-object sections
    # without needing generator changes for every new template family.
    for key, value in sorted(data.items()):
        if key in consumed_keys or key in {"meta", "schema_version", "family"}:
            continue
        if isinstance(value, list) and all(isinstance(x, dict) for x in value):
            for index, record in enumerate(value):
                yield key, index, record


def load_templates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: Counter[str] = Counter()
    stats: dict[str, Any] = {
        "template_files": {},
        "record_keys": Counter(),
        "warnings": [],
    }

    template_dir = ROOT / "templates"
    paths = sorted(template_dir.glob("*.json"))
    if not paths:
        raise TemplateLoadError(f"no template JSON files found under {template_dir}")

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateLoadError(f"invalid template JSON {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise TemplateLoadError(f"template file must contain a JSON object: {path}")

        file_family = data.get("family")
        file_count = 0
        for key, index, record in iter_template_records(path, data):
            stats["record_keys"][key] += 1
            fallback = f"{path.stem}_{key}_{index:04d}"
            item_id = normalize_id(record.get("id") or record.get("template_id"), fallback=fallback)
            if seen_ids[item_id]:
                item_id = f"{item_id}__dup{seen_ids[item_id]:03d}"
                stats["warnings"].append(f"renamed duplicate template id in {path.name}: {item_id}")
            seen_ids[item_id] += 1

            family = infer_family(key, record, file_family)
            authority = infer_authority(record, family)
            staleness = record.get("staleness")
            if staleness is None:
                if authority == "decoy":
                    staleness = "decoy"
                elif authority == "low" or record.get("superseded_by"):
                    staleness = "stale"
                else:
                    staleness = "current"
            supersedes = as_list(record.get("supersedes"))
            if record.get("superseded_by"):
                supersedes = []
            conflicts_with = as_list(record.get("conflicts_with"))
            if record.get("superseded_by"):
                conflicts_with.append(record.get("superseded_by"))

            tags = []
            tags.extend(as_list(record.get("tags")))
            for tag_key in ("category", "benchmark_name", "failure_type", "attack_type", "violation_type"):
                if record.get(tag_key):
                    tags.append(record[tag_key])

            item = {
                "id": item_id,
                "source_family": family,
                "authority": authority,
                "created_at": str(record.get("created_at", "2026-05-09")),
                "supersedes": sorted_unique_strings(supersedes),
                "tags": sorted_unique_strings(tags),
                "text": extract_text(record),
                "provenance": record.get("provenance", {"artifact_path": f"templates/{path.name}", "record_key": key, "record_index": index}),
                "staleness": str(staleness),
                "conflicts_with": sorted_unique_strings(conflicts_with),
                "safety_label": str(record.get("safety_label", "unsafe_decoy" if authority == "decoy" else "normal")),
            }
            items.append(item)
            file_count += 1
        stats["template_files"][path.name] = file_count

    if not items:
        raise TemplateLoadError("no template records loaded")
    repair_relationships(items, stats)
    stats["record_keys"] = dict(sorted(stats["record_keys"].items()))
    stats["template_files"] = dict(sorted(stats["template_files"].items()))
    stats["warnings"] = sorted(stats["warnings"])
    return items, stats


def repair_relationships(items: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    """Normalize relationship refs and drop refs that do not resolve to corpus IDs."""
    id_set = {str(item["id"]) for item in items}
    for item in items:
        for key in ("supersedes", "conflicts_with"):
            repaired: list[str] = []
            for ref in as_list(item.get(key)):
                candidates = [str(ref), normalize_id(ref, fallback="")]
                match = next((candidate for candidate in candidates if candidate in id_set), None)
                if match and match != item["id"]:
                    repaired.append(match)
                elif ref not in {None, ""}:
                    stats["warnings"].append(f"dropped dangling {key} ref on {item['id']}: {ref}")
            item[key] = sorted_unique_strings(repaired)


def expand_items(base_items: list[dict[str, Any]], target_tokens: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out = list(base_items)
    token_count = sum(rough_tokens(item["text"]) for item in out)
    index = 0
    filler_topics = [
        "routing evidence with provenance",
        "context packet compactness",
        "stale benchmark detection",
        "sandbox policy priority",
        "workflow trace recall",
        "debug failure caution",
    ]
    while token_count < target_tokens:
        base = rng.choice(base_items)
        topic = rng.choice(filler_topics)
        if base["authority"] == "decoy":
            support_authority = "decoy"
        elif base.get("staleness") == "stale" or base["authority"] == "low":
            support_authority = "low"
        else:
            support_authority = "medium"
        repeated = (
            f"Synthetic support note {index} for {topic}. "
            f"This note references source {base['id']} and preserves family {base['source_family']}. "
            "It is filler evidence for retrieval scale testing and should not override higher-authority records. "
        )
        item = {
            **base,
            "id": f"{base['id']}_support_{index:06d}",
            "authority": support_authority,
            "text": repeated * rng.randint(4, 9),
            "supersedes": [],
            "conflicts_with": [],
            "tags": sorted_unique_strings([*base.get("tags", []), "support", "scale_filler"]),
            "provenance": {
                "generated_from": base["id"],
                "generator": "generate_context_stress_dataset.py",
                "seed": seed,
                "support_index": index,
            },
        }
        out.append(item)
        token_count += rough_tokens(item["text"])
        index += 1
    return out


def load_cases() -> dict[str, Any]:
    return json.loads((ROOT / "eval" / "cases_seed.json").read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def build_manifest(out_dir: Path, scale: str, seed: int, target: int, items: list[dict[str, Any]], cases: dict[str, Any], template_stats: dict[str, Any]) -> dict[str, Any]:
    family_counts = Counter(item["source_family"] for item in items)
    authority_counts = Counter(item["authority"] for item in items)
    staleness_counts = Counter(item.get("staleness", "") for item in items)
    category_counts = Counter(case.get("category") for case in cases.get("cases", []))
    estimated_tokens = sum(rough_tokens(item["text"]) for item in items)
    files = {
        "corpus": "corpus/corpus_items.jsonl",
        "cases": "eval/cases.json",
    }
    file_hashes = {name: sha256_file(out_dir / rel) for name, rel in files.items()}
    return {
        "schema_version": "context_stress_manifest.v0.2",
        "dataset_id": f"context_stress_{scale}_{seed}",
        "scale": scale,
        "seed": seed,
        "created_at": DETERMINISTIC_CREATED_AT,
        "token_target": target,
        "estimated_tokens": estimated_tokens,
        "token_target_met": estimated_tokens >= target,
        "item_count": len(items),
        "case_count": len(cases.get("cases", [])),
        "source_family_counts": dict(sorted(family_counts.items())),
        "authority_counts": dict(sorted(authority_counts.items())),
        "staleness_counts": dict(sorted(staleness_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "template_stats": template_stats,
        "files": files,
        "file_sha256": file_hashes,
        "generator": {
            "script": "scripts/generate_context_stress_dataset.py",
            "rough_tokenizer": "whitespace_split_v1",
            "deterministic": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=sorted(TOKEN_TARGETS), default="smoke")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()

    target = TOKEN_TARGETS[args.scale]
    out_dir = ROOT / "out" / f"context_stress_{args.scale}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "corpus").mkdir(parents=True)
    (out_dir / "metadata").mkdir(parents=True)
    (out_dir / "eval").mkdir(parents=True)

    base_items, template_stats = load_templates()
    items = expand_items(base_items, target, args.seed)
    cases = load_cases()

    write_jsonl(out_dir / "corpus" / "corpus_items.jsonl", items)
    (out_dir / "eval" / "cases.json").write_text(json.dumps(cases, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    manifest = build_manifest(out_dir, args.scale, args.seed, target, items, cases, template_stats)
    (out_dir / "metadata" / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"dataset: {out_dir}")
    print(f"items: {len(items)}")
    print(f"estimated_tokens: {manifest['estimated_tokens']}")
    print(f"template_records: {len(base_items)}")


if __name__ == "__main__":
    main()
