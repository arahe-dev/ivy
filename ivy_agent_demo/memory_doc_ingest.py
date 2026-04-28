from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .memory_search import vectorize_memory_items
from .memory_store import DEFAULT_DB_PATH, MemoryStore, utc_now


DEFAULT_DOCS_ROOT = Path("C:/ivy/ivy/docs")
DEFAULT_SOURCE_FILES = [
    Path("C:/ivy/ivy/README.md"),
    Path("C:/ivy/README.md"),
    Path("C:/ivy/ivy_agent_demo/README.md"),
    Path("C:/ivy/ivy_agent_demo/policy.py"),
    Path("C:/ivy/ivy_agent_demo/validator.py"),
    Path("C:/ivy/ivy_agent_demo/tools.py"),
    Path("C:/ivy/ivy_agent_demo/schemas.py"),
]
DEFAULT_SCRIPT_ROOT = Path("C:/ivy/ivy/scripts")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def compact(text: str, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def classify_kind(path: Path, text: str) -> str:
    blob = f"{path.name} {text}".lower()
    if any(t in blob for t in ("sandbox", "absolute path", "path traversal", "delete", "network", "policy")):
        return "safety_rule"
    if "validator" in blob or "json" in blob:
        return "validator_rule"
    if "powershell" in blob or "python -m" in blob or ".ps1" in blob:
        return "runbook_command"
    if "benchmark" in blob or "qwen" in blob or "decode_tps" in blob:
        return "benchmark_guidance"
    if "workflow" in blob or "fs_read" in blob or "fs_write" in blob or "calc_eval" in blob:
        return "workflow_procedure"
    if "tool" in blob:
        return "tool_contract"
    return "doc_reference"


def iter_markdown_chunks(path: Path) -> list[dict[str, str]]:
    text = read_text(path)
    chunks: list[dict[str, str]] = []
    current_heading = path.name
    current: list[str] = []
    in_code = False
    code_lang = ""
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                body = "\n".join(current).strip()
                if body:
                    chunks.append({"heading": f"{current_heading} command", "text": body, "kind": "runbook_command"})
                current = []
                in_code = False
                code_lang = ""
            else:
                if current:
                    chunks.append({"heading": current_heading, "text": "\n".join(current), "kind": ""})
                    current = []
                in_code = True
                code_lang = line.strip().strip("`")
            continue
        if in_code:
            current.append(line)
            continue
        if line.startswith("#"):
            if current:
                chunks.append({"heading": current_heading, "text": "\n".join(current), "kind": ""})
                current = []
            current_heading = line.lstrip("#").strip() or path.name
        elif line.strip().startswith(("-", "*")) or "python -m " in line or "powershell " in line:
            current.append(line)
        elif line.strip() and any(t in line.lower() for t in ("sandbox", "policy", "memory", "packet", "eval", "benchmark", "qwen", "json", "tool", "workflow", "path")):
            current.append(line)
    if current:
        chunks.append({"heading": current_heading, "text": "\n".join(current), "kind": ""})
    return chunks


def iter_source_chunks(path: Path) -> list[dict[str, str]]:
    text = read_text(path)
    chunks = []
    for match in re.finditer(r"(?m)^(class|def)\s+([A-Za-z0-9_]+)", text):
        start = match.start()
        end_match = re.search(r"(?m)^(class|def)\s+", text[match.end():])
        end = match.end() + end_match.start() if end_match else min(len(text), start + 1800)
        body = text[start:end]
        if any(t in body.lower() for t in ("sandbox", "policy", "path", "json", "validate", "tool", "fs_write", "fs_read", "delete", "network")):
            chunks.append({"heading": f"{match.group(1)} {match.group(2)}", "text": body, "kind": ""})
    for line in text.splitlines():
        if any(t in line.lower() for t in ("sandbox", "absolute", "path traversal", "network", "delete", "fs_write", "fs_read", "json_validate")):
            chunks.append({"heading": f"{path.name} rule", "text": line.strip(), "kind": ""})
    return chunks


def build_memory_items(paths: list[Path], include_source: bool) -> list[dict[str, Any]]:
    items = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        chunks = iter_source_chunks(path) if include_source and path.suffix == ".py" else iter_markdown_chunks(path)
        for chunk in chunks:
            text = compact(f"{chunk['heading']}: {chunk['text']}", 700)
            if len(text) < 30:
                continue
            kind = chunk.get("kind") or classify_kind(path, text)
            items.append({
                "kind": kind,
                "text": text,
                "source_artifact_path": str(path),
                "importance": 0.55,
                "confidence": 0.85,
            })
    return items


def default_paths(docs_root: Path, include_source: bool) -> list[Path]:
    paths = []
    if docs_root.exists():
        paths.extend(sorted(docs_root.glob("*.md")))
    paths.extend([p for p in DEFAULT_SOURCE_FILES if p.exists()])
    if DEFAULT_SCRIPT_ROOT.exists():
        paths.extend(sorted(DEFAULT_SCRIPT_ROOT.glob("*.ps1")))
        paths.extend(sorted(DEFAULT_SCRIPT_ROOT.glob("*.py")))
    if not include_source:
        paths = [p for p in paths if p.suffix.lower() in {".md", ".ps1"}]
    return paths


def ingest_docs(db_path: str | Path, paths: list[Path], include_source: bool, dry_run: bool = False) -> dict[str, Any]:
    items = build_memory_items(paths, include_source)
    if dry_run:
        return {"dry_run": True, "source_files": len(paths), "memory_items": len(items), "kinds": sorted({i["kind"] for i in items})}
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    inserted = 0
    try:
        with conn:
            ep_cur = conn.execute(
                """
                INSERT INTO episodes(run_id, created_at, task_text, outcome, success, artifact_path, source_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("docs-source-ingest", utc_now(), "docs/source memory coverage ingestion", "ingested", 1, "docs/source", "docs_source"),
            )
            episode_id = int(ep_cur.lastrowid)
            for path in paths:
                if path.exists() and path.is_file():
                    text = read_text(path)
                    conn.execute(
                        "INSERT OR IGNORE INTO artifacts(episode_id, path, kind, sha256, created_at) VALUES (?, ?, ?, ?, ?)",
                        (episode_id, str(path), path.suffix.lstrip(".") or "source", sha256_text(text), utc_now()),
                    )
            existing = {r[0] for r in conn.execute("SELECT text || '|' || COALESCE(source_artifact_path,'') FROM memory_items")}
            for item in items:
                key = item["text"] + "|" + item["source_artifact_path"]
                if key in existing:
                    continue
                store.insert_memory_item(conn, source_episode_id=episode_id, status="active", **item)
                inserted += 1
    finally:
        conn.close()
    vectorized = vectorize_memory_items(db_path)
    return {"dry_run": False, "source_files": len(paths), "memory_items_built": len(items), "memory_items_inserted": inserted, "vectorized": vectorized}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest IVY docs/source into passive memory.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--docs-root", default=str(DEFAULT_DOCS_ROOT))
    parser.add_argument("--include-source", action="store_true")
    parser.add_argument("--all-defaults", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    docs_root = Path(args.docs_root)
    paths = default_paths(docs_root, args.include_source or args.all_defaults)
    if not args.all_defaults and args.docs_root:
        paths = sorted(docs_root.glob("*.md")) if docs_root.exists() else []
        if args.include_source:
            paths.extend([p for p in DEFAULT_SOURCE_FILES if p.exists()])
    result = ingest_docs(args.db, paths, args.include_source or args.all_defaults, args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
