from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError:  # pragma: no cover - exercised only in an unbootstrapped env
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]
    ValidationError = Exception  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

REQUIRED_CATEGORIES = {
    "general",
    "local_codebase",
    "exact_command",
    "benchmark",
    "safety",
    "workflow",
    "debug",
    "unanswerable",
    "stale_conflict",
    "adversarial_decoy",
}
VALID_SCALES = {"smoke": 50_000, "medium": 200_000, "stress": 2_000_000, "ivy_real": 1}
REQUIRED_ITEM_KEYS = (
    "id",
    "source_family",
    "authority",
    "created_at",
    "supersedes",
    "tags",
    "text",
    "provenance",
    "staleness",
    "conflicts_with",
    "safety_label",
)


def rough_tokens(text: str) -> int:
    return max(1, len(str(text).split()))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON at {path}: {exc}")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
    return None


def load_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSONL at {path}:{lineno}: {exc}")
                    continue
                if not isinstance(row, dict):
                    errors.append(f"corpus row at {path}:{lineno} is not an object")
                    continue
                row["__line__"] = lineno
                rows.append(row)
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
    return rows


def schema_payload(name: str, errors: list[str]) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    payload = load_json(path, errors)
    if not isinstance(payload, dict):
        errors.append(f"schema {path} root must be an object")
        return {}
    return payload


def format_schema_error(exc: ValidationError) -> str:
    location = "$" if not exc.path else "$." + ".".join(str(part) for part in exc.path)
    return f"{location}: {exc.message}"


def validate_schema(payload: Any, schema: dict[str, Any], label: str, errors: list[str]) -> None:
    if Draft202012Validator is None or FormatChecker is None:
        errors.append("jsonschema is not installed; run `python -m pip install -e .[test]` or install project dependencies")
        return
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for exc in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        errors.append(f"{label} schema error: {format_schema_error(exc)}")


def clean_item(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "__line__"}


def validate_item_semantics(items: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> set[str]:
    ids: list[str] = []
    id_lines: dict[str, list[int]] = defaultdict(list)
    for item in items:
        line = int(item.get("__line__", 0))
        item_id = item.get("id")
        ids.append(str(item_id))
        id_lines[str(item_id)].append(line)
        for key in REQUIRED_ITEM_KEYS:
            if key not in item:
                errors.append(f"item at line {line} missing {key}")
        if not isinstance(item.get("id"), str) or not item.get("id"):
            errors.append(f"item at line {line} has empty/non-string id")
        if not isinstance(item.get("text"), str) or not item.get("text", "").strip():
            errors.append(f"item {item_id!r} line {line} has empty/non-string text")
        for list_key in ("supersedes", "tags", "conflicts_with"):
            if list_key in item and not isinstance(item[list_key], list):
                errors.append(f"item {item_id!r} line {line} field {list_key} must be a list")
        if item.get("authority") == "decoy":
            if item.get("source_family") != "distractor":
                errors.append(f"decoy item {item_id!r} line {line} must use source_family='distractor'")
            if item.get("safety_label") not in {"unsafe_decoy", "secret_like"}:
                errors.append(f"decoy item {item_id!r} line {line} must use unsafe/secret safety_label")

    duplicates = {item_id: lines for item_id, lines in id_lines.items() if len(lines) > 1}
    for item_id, lines in sorted(duplicates.items()):
        errors.append(f"duplicate corpus item ID {item_id!r} at lines {lines}")

    id_set = {str(item.get("id")) for item in items}
    for item in items:
        item_id = str(item.get("id"))
        line = int(item.get("__line__", 0))
        for key in ("supersedes", "conflicts_with"):
            for target in item.get(key, []) or []:
                if target not in id_set:
                    errors.append(f"item {item_id!r} line {line} has dangling {key} reference {target!r}")
                if target == item_id:
                    errors.append(f"item {item_id!r} line {line} has self {key} reference")
        provenance = item.get("provenance", {})
        if isinstance(provenance, dict) and provenance.get("generated_from") and provenance["generated_from"] not in id_set:
            errors.append(f"item {item_id!r} line {line} has dangling generated_from reference {provenance['generated_from']!r}")
        if ("_support_" in item_id or "support" in item.get("tags", [])) and (item.get("supersedes") or item.get("conflicts_with")):
            warnings.append(f"support item {item_id!r} line {line} carries relationship refs")

    return id_set


def validate_cases_semantics(
    cases: list[dict[str, Any]],
    id_set: set[str],
    errors: list[str],
    warnings: list[str],
) -> Counter[str]:
    category_counts = Counter(str(case.get("category")) for case in cases)
    missing_categories = sorted(REQUIRED_CATEGORIES - set(category_counts))
    if missing_categories:
        errors.append(f"missing categories: {missing_categories}")

    case_ids: Counter[str] = Counter(str(case.get("id")) for case in cases)
    for case_id, count in sorted(case_ids.items()):
        if count > 1:
            errors.append(f"duplicate case ID {case_id!r}")

    for idx, case in enumerate(cases):
        case_id = case.get("id", f"case[{idx}]")
        for source_key in ("required_source_ids", "forbidden_source_ids"):
            sources = case.get(source_key, [])
            if not isinstance(sources, list):
                errors.append(f"case {case_id!r} field {source_key} must be a list")
                continue
            for source_id in sources:
                if source_id not in id_set:
                    errors.append(f"case {case_id!r} missing {source_key[:-1]} {source_id!r}")
        ratio = case.get("retrieval_ratio_target")
        if ratio is not None:
            if not (
                isinstance(ratio, list)
                and len(ratio) == 2
                and all(isinstance(x, (int, float)) for x in ratio)
                and 0 <= ratio[0] <= ratio[1] <= 1
            ):
                errors.append(f"case {case_id!r} has invalid retrieval_ratio_target {ratio!r}")
        if case.get("must_abstain") and case.get("required_source_ids"):
            warnings.append(f"case {case_id!r} must_abstain=true but has required_source_ids")
    return category_counts


def validate_manifest_semantics(
    manifest: dict[str, Any],
    root: Path,
    items: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    category_counts: Counter[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if manifest.get("item_count") != len(items):
        errors.append(f"manifest item_count {manifest.get('item_count')} does not match corpus {len(items)}")
    if manifest.get("case_count") != len(cases):
        errors.append(f"manifest case_count {manifest.get('case_count')} does not match cases {len(cases)}")

    estimated_tokens = sum(rough_tokens(item.get("text", "")) for item in items)
    if manifest.get("estimated_tokens") != estimated_tokens:
        errors.append(f"manifest estimated_tokens {manifest.get('estimated_tokens')} does not match recomputed {estimated_tokens}")

    scale = manifest.get("scale")
    if scale not in VALID_SCALES:
        errors.append(f"manifest scale {scale!r} is not one of {sorted(VALID_SCALES)}")
    else:
        target = VALID_SCALES[scale]
        if manifest.get("token_target") != target:
            errors.append(f"manifest token_target {manifest.get('token_target')} does not match scale {scale!r} target {target}")
        if estimated_tokens < target:
            errors.append(f"estimated tokens {estimated_tokens} below target {target} for scale {scale}")
        if manifest.get("token_target_met") != (estimated_tokens >= target):
            errors.append("manifest token_target_met does not match recomputed token target status")

    family_counts = Counter(item.get("source_family") for item in items)
    authority_counts = Counter(item.get("authority") for item in items)
    staleness_counts = Counter(item.get("staleness") for item in items)
    if manifest.get("source_family_counts") != dict(sorted(family_counts.items())):
        errors.append("manifest source_family_counts does not match corpus")
    if manifest.get("authority_counts") != dict(sorted(authority_counts.items())):
        errors.append("manifest authority_counts does not match corpus")
    if manifest.get("staleness_counts") != dict(sorted(staleness_counts.items())):
        errors.append("manifest staleness_counts does not match corpus")
    if manifest.get("category_counts") != dict(sorted(category_counts.items())):
        errors.append("manifest category_counts does not match cases")

    files = manifest.get("files", {})
    hashes = manifest.get("file_sha256", {})
    if not isinstance(files, dict):
        errors.append("manifest files must be an object")
        return
    if not isinstance(hashes, dict):
        errors.append("manifest file_sha256 must be an object")
        hashes = {}
    for name, rel in sorted(files.items()):
        if not isinstance(rel, str):
            errors.append(f"manifest file entry {name!r} is not a string")
            continue
        path = root / rel
        if not path.exists():
            errors.append(f"manifest file entry {name!r} points to missing file {path}")
            continue
        if name in hashes:
            actual = sha256_file(path)
            if hashes[name] != actual:
                errors.append(f"manifest file_sha256[{name!r}] mismatch: {hashes[name]} != {actual}")
        else:
            warnings.append(f"manifest has no file_sha256 for {name!r}")


def validate_dataset(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    corpus_path = root / "corpus" / "corpus_items.jsonl"
    manifest_path = root / "metadata" / "dataset_manifest.json"
    cases_path = root / "eval" / "cases.json"

    errors: list[str] = []
    warnings: list[str] = []
    for path in (corpus_path, manifest_path, cases_path):
        if not path.exists():
            errors.append(f"missing file: {path}")
    if errors:
        return errors, warnings, {}

    manifest_schema = schema_payload("dataset_manifest.schema.json", errors)
    corpus_schema = schema_payload("corpus_item.schema.json", errors)
    eval_cases_schema = schema_payload("eval_cases.schema.json", errors)
    eval_case_schema = schema_payload("eval_case.schema.json", errors)

    items = load_jsonl(corpus_path, errors)
    manifest = load_json(manifest_path, errors)
    cases_payload = load_json(cases_path, errors)
    if not isinstance(manifest, dict):
        errors.append("manifest root must be an object")
        manifest = {}
    if not isinstance(cases_payload, dict):
        errors.append("cases root must be an object")
        cases_payload = {}
    cases = cases_payload.get("cases", [])
    if not isinstance(cases, list):
        errors.append("cases payload field 'cases' must be a list")
        cases = []
    cases = [case for case in cases if isinstance(case, dict)]

    validate_schema(manifest, manifest_schema, "manifest", errors)
    validate_schema(cases_payload, eval_cases_schema, "cases file", errors)
    for index, case in enumerate(cases):
        validate_schema(case, eval_case_schema, f"case[{index}:{case.get('id', '<missing>')}]", errors)
    for item in items:
        validate_schema(clean_item(item), corpus_schema, f"corpus line {item.get('__line__')}", errors)

    id_set = validate_item_semantics(items, errors, warnings)
    category_counts = validate_cases_semantics(cases, id_set, errors, warnings)

    stale_or_conflict = sum(
        1
        for item in items
        if item.get("staleness") in {"stale", "decoy"} or item.get("conflicts_with") or item.get("authority") == "decoy"
    )
    if stale_or_conflict == 0:
        errors.append("no stale/conflict/decoy items found")

    validate_manifest_semantics(manifest, root, items, cases, category_counts, errors, warnings)

    summary = {
        "items": len(items),
        "cases": len(cases),
        "estimated_tokens": sum(rough_tokens(item.get("text", "")) for item in items),
        "categories": dict(sorted(category_counts.items())),
        "source_families": dict(sorted(Counter(item.get("source_family") for item in items).items())),
        "authorities": dict(sorted(Counter(item.get("authority") for item in items).items())),
        "staleness": dict(sorted(Counter(item.get("staleness") for item in items).items())),
    }
    return errors, warnings, summary


def print_report(errors: list[str], warnings: list[str], summary: dict[str, Any]) -> None:
    status = "FAIL" if errors else "PASS"
    print(status)
    if errors:
        print(f"errors: {len(errors)}")
        for error in errors[:200]:
            print(f"- {error}")
        if len(errors) > 200:
            print(f"- ... {len(errors) - 200} more errors omitted")
    if warnings:
        print(f"warnings: {len(warnings)}")
        for warning in warnings[:50]:
            print(f"- {warning}")
        if len(warnings) > 50:
            print(f"- ... {len(warnings) - 50} more warnings omitted")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()
    errors, warnings, summary = validate_dataset(Path(args.dataset))
    print_report(errors, warnings, summary)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
