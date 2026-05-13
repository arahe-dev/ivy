from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MOME_MOCE_SCRIPTS = REPO_ROOT / "MoME-MoCE-Exp" / "scripts"
DEFAULT_MEMORY_JSONL = REPO_ROOT / "runs" / "acca_milestone_memory" / "memory_records.jsonl"

if str(MOME_MOCE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(MOME_MOCE_SCRIPTS))

from memory_write_barrier import append_memory_record, validate_memory_record  # noqa: E402


def _git(args: list[str], *, cwd: Path = REPO_ROOT) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _commit_summary(commit: str, *, repo: Path = REPO_ROOT) -> dict[str, Any]:
    sha = _git(["rev-parse", "--short", commit], cwd=repo)
    subject = _git(["show", "-s", "--format=%s", commit], cwd=repo)
    files = _git(["show", "--name-only", "--format=", commit], cwd=repo).splitlines()
    return {"sha": sha, "subject": subject, "files": [line for line in files if line.strip()]}


def _safe_source_path(source_path: str | None) -> str:
    if source_path:
        path = source_path.replace("\\", "/")
    else:
        path = "runs/acca_milestone_memory/memory_records.jsonl"
    root = str(REPO_ROOT).replace("\\", "/").rstrip("/") + "/"
    if path.lower().startswith(root.lower()):
        path = path[len(root) :]
    if ":" in path[:3] or path.startswith("/"):
        path = "external/" + path.replace(":", "").lstrip("/")
    return path


def build_milestone_record(
    *,
    commit: str,
    note: str,
    tests: dict[str, Any] | None = None,
    source_path: str | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    summary = _commit_summary(commit, repo=repo)
    tests_text = ""
    if tests:
        tests_text = " Tests: " + json.dumps(tests, sort_keys=True, ensure_ascii=True)
    changed = ", ".join(summary["files"][:8])
    if len(summary["files"]) > 8:
        changed += f", +{len(summary['files']) - 8} more"
    text = (
        f"Milestone commit {summary['sha']} ({summary['subject']}) completed. "
        f"Note: {note.strip()} "
        f"Changed files: {changed or 'none'}.{tests_text}"
    )
    return {
        "text": text,
        "source_family": "workflow_trace",
        "authority": "high",
        "staleness": "current",
        "source_path": _safe_source_path(source_path),
        "safety_label": "normal",
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
    }


def load_tests(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create milestone memory through the ACCA write barrier.")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--note", required=True)
    parser.add_argument("--tests-json", type=Path)
    parser.add_argument("--source-path")
    parser.add_argument("--memory-jsonl", type=Path, default=DEFAULT_MEMORY_JSONL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    record = build_milestone_record(
        commit=args.commit,
        note=args.note,
        tests=load_tests(args.tests_json),
        source_path=args.source_path,
    )
    payload = validate_memory_record(record) if args.dry_run else append_memory_record(args.memory_jsonl, record)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
