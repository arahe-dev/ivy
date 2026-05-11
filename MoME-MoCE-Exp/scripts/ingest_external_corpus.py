from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from generate_ivy_real_dataset import CATEGORIES, sha256_file
except ModuleNotFoundError:
    from scripts.generate_ivy_real_dataset import CATEGORIES, sha256_file


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".ps1", ".ts", ".tsx", ".js", ".jsx", ".rs", ".json", ".toml", ".yaml", ".yml"}
SKIP_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
    "release-artifacts",
    "research-runs",
    "target",
    "__pycache__",
}
SECRET_RE = re.compile(r"(api[_-]?key|secret|token|password|private key|-----begin)", re.IGNORECASE)


def slug(value: str, *, limit: int = 56) -> str:
    out = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (out or "item")[:limit].strip("_") or "item"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def rough_tokens(text: str) -> int:
    return max(1, len(text.split()))


def iter_files(source_roots: list[Path], extensions: set[str], max_files: int | None) -> Iterable[tuple[int, Path, Path]]:
    count = 0
    for root_index, root in enumerate(source_roots):
        for path in sorted(root.rglob("*")):
            if max_files is not None and count >= max_files:
                return
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            if path.suffix.lower() not in extensions:
                continue
            count += 1
            yield root_index, root, path


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def markdown_sections(text: str) -> list[tuple[str, int, int]]:
    matches = list(re.finditer(r"(?m)^(#{1,4})\s+(.+?)\s*$", text))
    if not matches:
        return [("document", 0, len(text))]
    sections: list[tuple[str, int, int]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        title = match.group(2).strip()
        sections.append((title, start, end))
    prefix = text[: matches[0].start()].strip()
    if prefix:
        sections.insert(0, ("front matter", 0, matches[0].start()))
    return sections


def split_long_chunk(title: str, text: str, *, max_chars: int) -> list[tuple[str, str]]:
    compact = text.strip()
    if len(compact) <= max_chars:
        return [(title, compact)] if compact else []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", compact) if part.strip()]
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    part_index = 1
    for paragraph in paragraphs:
        proposed = "\n\n".join([*current, paragraph])
        if current and len(proposed) > max_chars:
            chunks.append((f"{title} part {part_index}", "\n\n".join(current)))
            current = [paragraph]
            part_index += 1
        else:
            current.append(paragraph)
    if current:
        chunks.append((f"{title} part {part_index}" if part_index > 1 else title, "\n\n".join(current)))
    return chunks


def classify_family(path: Path, text: str) -> str:
    p = str(path).lower().replace("\\", "/")
    t = text.lower()
    if any(term in p for term in ["/test", "/tests", "smoke", "checklist"]) or any(term in t for term in ["steps", "run ", "powershell", "command"]):
        return "runbook"
    if path.suffix.lower() in {".py", ".ps1", ".ts", ".tsx", ".js", ".jsx", ".rs"}:
        return "source_code"
    if any(term in p for term in ["security", "policy", "risk"]) or any(term in t for term in ["least privilege", "safety", "policy", "forbidden"]):
        return "safety_policy"
    if any(term in p for term in ["benchmark", "report", "status", "result"]):
        return "benchmark_artifact"
    if any(term in p for term in ["error", "bug", "debug", "failure"]):
        return "debug_failure"
    if any(term in p for term in ["workflow", "trace", "phase"]):
        return "workflow_trace"
    return "doc_memory"


def classify_staleness(path: Path, text: str) -> str:
    blob = f"{path} {text[:500]}".lower()
    if any(term in blob for term in ["deprecated", "stale", "old note", "obsolete", "superseded"]):
        return "stale"
    return "current"


def authority_for(family: str, path: Path) -> str:
    p = str(path).lower().replace("\\", "/")
    if family in {"safety_policy", "source_code"}:
        return "high"
    if "/docs/" in p or p.endswith("readme.md") or "readme" in path.name.lower():
        return "high"
    if family in {"runbook", "workflow_trace", "benchmark_artifact"}:
        return "medium"
    return "medium"


def tags_for(path: Path, title: str, text: str, source_name: str) -> list[str]:
    raw = [source_name, path.stem, title]
    lower = text.lower()
    for term in [
        "signal",
        "tailscale",
        "web push",
        "iphone",
        "event log",
        "sqlite",
        "daemon",
        "worker",
        "recall",
        "excalidraw",
        "ai context",
        "text graph",
        "graph ir",
        "backlinks",
        "subpages",
    ]:
        if term in lower:
            raw.append(term)
    out = []
    for value in raw:
        cleaned = re.sub(r"\s+", " ", str(value).strip().lower())
        if cleaned and cleaned not in out:
            out.append(cleaned[:96])
    return out[:12] or ["external"]


def item_from_chunk(
    *,
    root_index: int,
    root: Path,
    path: Path,
    source_name: str,
    title: str,
    text: str,
    chunk_index: int,
    offset_start: int,
    offset_end: int,
) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    family = classify_family(path, text)
    staleness = classify_staleness(path, text)
    safety_label = "secret_like" if SECRET_RE.search(text) else "normal"
    exposure_policy = "forbidden" if safety_label == "secret_like" else "frontier_ok"
    authority = "low" if staleness == "stale" else authority_for(family, path)
    digest = sha256_text(f"{root_index}:{rel}:{title}:{chunk_index}:{text}")[:12]
    item_id = f"ing_{slug(source_name, limit=24)}_{slug(path.stem, limit=28)}_{chunk_index}_{digest}"
    return {
        "id": item_id,
        "source_family": family,
        "authority": authority,
        "created_at": "2026-05-11",
        "supersedes": [],
        "tags": tags_for(path, title, text, source_name),
        "text": " ".join(text.split())[:20000],
        "provenance": {
            "artifact_path": f"root/external/{slug(source_name)}/{rel}",
            "source_hash": sha256_text(text)[:32],
            "line_start": line_for_offset(path.read_text(encoding="utf-8", errors="ignore"), offset_start),
            "line_end": line_for_offset(path.read_text(encoding="utf-8", errors="ignore"), offset_end),
            "generator": "scripts/ingest_external_corpus.py",
            "record_index": chunk_index,
        },
        "staleness": staleness,
        "conflicts_with": [],
        "safety_label": safety_label,
        "taint_labels": ["secret_like"] if safety_label == "secret_like" else ["normal"],
        "exposure_policy": exposure_policy,
        "claim_type": "code_reference" if family == "source_code" else "fact",
        "canonical_for": [slug(f"{source_name} {path.stem} {title}", limit=120)],
    }


def ingest(source_roots: list[Path], *, max_chars: int, max_files: int | None, extensions: set[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for root_index, root, path in iter_files(source_roots, extensions, max_files):
        source_name = root.name or f"source_{root_index}"
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text.strip():
            continue
        sections = markdown_sections(text) if path.suffix.lower() in {".md", ".rst"} else [("source file", 0, len(text))]
        chunk_index = 0
        for title, start, end in sections:
            section_text = text[start:end].strip()
            for chunk_title, chunk_text in split_long_chunk(title, section_text, max_chars=max_chars):
                if rough_tokens(chunk_text) < 8:
                    continue
                item = item_from_chunk(
                    root_index=root_index,
                    root=root,
                    path=path,
                    source_name=source_name,
                    title=chunk_title,
                    text=chunk_text,
                    chunk_index=chunk_index,
                    offset_start=start,
                    offset_end=end,
                )
                chunk_index += 1
                if item["id"] not in seen_ids:
                    items.append(item)
                    seen_ids.add(item["id"])
    return items


def find_item(items: list[dict[str, Any]], required_terms: list[str], avoid_terms: list[str] | None = None) -> str | None:
    avoid_terms = avoid_terms or []
    ranked = []
    for item in items:
        blob = (item["id"] + " " + " ".join(item.get("tags", [])) + " " + item["text"]).lower()
        if all(term.lower() in blob for term in required_terms) and not any(term.lower() in blob for term in avoid_terms):
            ranked.append((len(item["text"]), item["id"]))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][1]


def case(case_id: str, query: str, required_id: str, *, category: str = "general", safety: bool = False) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": "safety" if safety else category,
        "query": query,
        "should_retrieve": True,
        "retrieval_ratio_target": [0.0, 0.1],
        "required_source_ids": [required_id],
        "forbidden_source_ids": [],
        "expected_terms": [],
        "forbidden_terms": [],
        "must_abstain": False,
        "requires_conflict_resolution": False,
        "requires_safety_priority": safety,
        "provenance_required": True,
        "max_evidence_items": 1,
        "answer_contract": "answer",
        "notes": "CP26 generated smoke case over ingested external corpus.",
    }


def signal_recall_cases(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = [
        (
            "cp26_ingest_signal_iphone_webpush",
            "How does Signal reach an iPhone through Web Push and Tailscale Serve?",
            ["signal", "iphone", "web push", "tailscale"],
            [],
            "exact_command",
            False,
        ),
        (
            "cp26_ingest_signal_event_log",
            "What Signal primitive is the append-only SQLite event log source of truth?",
            ["signal", "event log", "source of truth"],
            [],
            "workflow",
            False,
        ),
        (
            "cp26_ingest_signal_daemon_worker_boundary",
            "What is the Signal daemon and worker execution boundary?",
            ["daemon", "worker", "policy"],
            [],
            "safety",
            True,
        ),
        (
            "cp26_ingest_recall_ai_context",
            "What does Recall Board export so AI can understand a board without screenshots?",
            ["screenshots", "expensive", "ambiguous", "text graph"],
            [],
            "general",
            False,
        ),
        (
            "cp26_ingest_recall_graph_ir",
            "What is Recall Graph IR for in the AI to Excalidraw pipeline?",
            ["import recall graph ir json", "export board state"],
            [],
            "local_codebase",
            False,
        ),
    ]
    cases = []
    for case_id, query, terms, avoid, category, safety in specs:
        item_id = find_item(items, terms, avoid)
        if item_id is not None:
            cases.append(case(case_id, query, item_id, category=category, safety=safety))
    cases.append(
        {
            "id": "cp26_ingest_recall_cloud_price_abstain",
            "category": "unanswerable",
            "query": "What is the latest production price for Recall Cloud?",
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
            "notes": "CP26 generated unsupported external commercial-fact abstention case.",
        }
    )
    return cases


def write_dataset(
    output: Path,
    *,
    source_roots: list[Path],
    items: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    dataset_id: str,
) -> dict[str, Any]:
    if output.exists():
        import shutil

        shutil.rmtree(output)
    (output / "corpus").mkdir(parents=True)
    (output / "eval").mkdir(parents=True)
    (output / "metadata").mkdir(parents=True)
    corpus_path = output / "corpus" / "corpus_items.jsonl"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    cases_path = output / "eval" / "cases.json"
    cases_path.write_text(json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    category_counts = Counter(row["category"] for row in cases)
    manifest = {
        "schema_version": "context_stress_dataset_manifest.v0.1",
        "dataset_id": dataset_id,
        "created_at": datetime(2026, 5, 11, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_count": len(cases),
        "corpus_items": len(items),
        "category_counts": {key: category_counts[key] for key in CATEGORIES},
        "source_roots": [str(path) for path in source_roots],
        "source_families": dict(Counter(item["source_family"] for item in items)),
        "file_sha256": {
            "corpus": sha256_file(corpus_path),
            "cases": sha256_file(cases_path),
        },
        "generator": {
            "script": "scripts/ingest_external_corpus.py",
            "deterministic": True,
        },
        "generation": {
            "type": "cp26_external_ingestion",
            "notes": "Generic folder/repo ingestion into ACCA corpus item shape with optional discovered smoke cases.",
        },
    }
    (output / "metadata" / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output), **manifest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CP26 ingest arbitrary folders/repos into an ACCA-compatible corpus dataset.")
    parser.add_argument("--source-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "out" / "context_stress_external_ingested")
    parser.add_argument("--dataset-id", default="context_stress_external_ingested")
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--extension", action="append", default=None, help="File extension to include, e.g. .md. Defaults to common doc/source extensions.")
    parser.add_argument("--seed-signal-recall-cases", action="store_true")
    args = parser.parse_args(argv)

    source_roots = [path if path.is_absolute() else Path.cwd() / path for path in args.source_root]
    missing = [str(path) for path in source_roots if not path.exists()]
    if missing:
        raise FileNotFoundError(f"source root(s) not found: {missing}")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.extension} if args.extension else DEFAULT_EXTENSIONS
    items = ingest(source_roots, max_chars=args.max_chars, max_files=args.max_files, extensions=extensions)
    cases = signal_recall_cases(items) if args.seed_signal_recall_cases else []
    payload = write_dataset(output, source_roots=source_roots, items=items, cases=cases, dataset_id=args.dataset_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if items and (not args.seed_signal_recall_cases or len(cases) >= 4) else 1


if __name__ == "__main__":
    raise SystemExit(main())
