from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BufferedReader, BufferedWriter
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
MOME_ROOT = REPO_ROOT / "MoME-MoCE-Exp"
DEFAULT_STORE = REPO_ROOT / ".ivy-context-memory"
DEFAULT_DATASET = "context_memory_live"
DEFAULT_WARM_QUERIES = [
    "What did CP28 show about final answer packet formats?",
    "What MCP tools does ivy-context-memory expose?",
    "What is the latest CP42 rebuild policy versus stale memory?",
    "What is today's Bitcoin price?",
]

if str(MOME_ROOT) not in sys.path:
    sys.path.insert(0, str(MOME_ROOT))
if str(MOME_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MOME_ROOT / "scripts"))

try:
    from scripts.ingest_external_corpus import DEFAULT_EXTENSIONS, SKIP_DIRS, ingest_file  # type: ignore  # noqa: E402
    from scripts.mome_moce_harness import (  # type: ignore  # noqa: E402
        CorpusItem,
        MoMEMoCERouter,
        derive_exposure_policy,
        derive_taint_labels,
        load_corpus,
        norm,
        rough_tokens,
        split_identifier,
        tokenize,
    )
    from scripts.run_packet_format_ab import render_variant  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    from ingest_external_corpus import DEFAULT_EXTENSIONS, SKIP_DIRS, ingest_file  # type: ignore  # noqa: E402
    from mome_moce_harness import (  # type: ignore  # noqa: E402
        CorpusItem,
        MoMEMoCERouter,
        derive_exposure_policy,
        derive_taint_labels,
        load_corpus,
        norm,
        rough_tokens,
        split_identifier,
        tokenize,
    )
    from run_packet_format_ab import render_variant  # type: ignore  # noqa: E402


SECRET_RE = re.compile(r"\b(api[_ -]?key|password|private[_ -]?key|secret|token|bearer)\b", re.I)
REDACT_RE = re.compile(r"\b(api[_ -]?key|password|private[_ -]?key|secret|token|bearer)\s*[:=]\s*\S+", re.I)
_QUERY_INDEX_CACHE: dict[str, tuple[int, int, dict[str, Any]]] = {}
_CORPUS_ITEM_CACHE: dict[tuple[str, str, int], CorpusItem] = {}
_ITEM_FEATURE_CACHE: dict[tuple[str, str, int], dict[str, Any]] = {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def slug(value: str, limit: int = 80) -> str:
    out = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (out or "item")[:limit].strip("_") or "item"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_store(path: Path | None) -> Path:
    return (path or Path(os.environ.get("IVY_CONTEXT_MEMORY_STORE", DEFAULT_STORE))).resolve()


def state_path(store: Path) -> Path:
    return store / "state.json"


def notes_path(store: Path) -> Path:
    return store / "notes.jsonl"


def sessions_dir(store: Path) -> Path:
    return store / "sessions"


def deltas_path(store: Path) -> Path:
    return store / "memory_deltas.jsonl"


def dataset_path(store: Path) -> Path:
    return store / "datasets" / DEFAULT_DATASET


def index_path(store: Path) -> Path:
    return store / "index" / "corpus_index.json"


def query_subset_path(store: Path) -> Path:
    return store / "query_subset"


def build_cache_path(store: Path) -> Path:
    return store / "cache" / "build_fingerprint.json"


def runtime_policy_path(store: Path) -> Path:
    return store / "policy" / "autoresearch_policy.json"


def chunk_cache_path(store: Path, root: Path, path: Path) -> Path:
    key = content_hash(f"{root.resolve()}::{path.relative_to(root).as_posix()}")[:24]
    return store / "cache" / "chunks" / f"{key}.json"


def load_state(store: Path) -> dict[str, Any]:
    path = state_path(store)
    if not path.exists():
        return {
            "schema_version": "ivy_context_memory.state.v0.1",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "source_roots": [],
            "last_build": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(store: Path, state: dict[str, Any]) -> None:
    store.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    final_path = state_path(store)
    tmp_path = final_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(final_path)


def init_store(store: Path) -> dict[str, Any]:
    store.mkdir(parents=True, exist_ok=True)
    (store / "datasets").mkdir(parents=True, exist_ok=True)
    (store / "packets").mkdir(parents=True, exist_ok=True)
    sessions_dir(store).mkdir(parents=True, exist_ok=True)
    (store / "cache").mkdir(parents=True, exist_ok=True)
    state = load_state(store)
    save_state(store, state)
    notes_path(store).touch(exist_ok=True)
    deltas_path(store).touch(exist_ok=True)
    return {"ok": True, "store": str(store), "dataset": str(dataset_path(store)), "source_roots": state["source_roots"]}


def read_notes(store: Path) -> list[dict[str, Any]]:
    path = notes_path(store)
    if not path.exists():
        return []
    notes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            notes.append(json.loads(line))
    return notes


def iter_fingerprint_files(roots: list[Path], extensions: set[str], max_files: int | None) -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if max_files is not None and len(files) >= max_files:
                return files
            if not path.is_file():
                continue
            try:
                rel_parts = path.relative_to(root).parts
            except ValueError:
                continue
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            if path.suffix.lower() not in extensions:
                continue
            files.append((root, path))
    return files


def source_fingerprint(store: Path, roots: list[Path], *, extensions: set[str], max_files: int | None) -> dict[str, Any]:
    rows: list[str] = []
    total_size = 0
    for root, path in iter_fingerprint_files(roots, extensions, max_files):
        try:
            stat = path.stat()
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        total_size += int(stat.st_size)
        rows.append(f"{root.resolve()}::{rel}::{int(stat.st_size)}::{int(stat.st_mtime_ns)}")
    notes_blob = notes_path(store).read_text(encoding="utf-8") if notes_path(store).exists() else ""
    payload = {
        "schema_version": "ivy_context_memory.build_fingerprint.v0.1",
        "source_roots": [str(path.resolve()) for path in roots],
        "extensions": sorted(extensions),
        "max_files": max_files,
        "file_count": len(rows),
        "total_size": total_size,
        "notes_sha256": content_hash(notes_blob),
        "fingerprint_sha256": content_hash("\n".join(rows) + "\nnotes:" + content_hash(notes_blob)),
    }
    return payload


def cached_ingest(store: Path, roots: list[Path], *, max_chars: int, max_files: int | None, extensions: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    hit_files = 0
    miss_files = 0
    for root_index, root in enumerate(roots):
        source_name = root.name or f"source_{root_index}"
        for file_root, path in iter_fingerprint_files([root], extensions, max_files):
            try:
                stat = path.stat()
            except OSError:
                continue
            cache_path = chunk_cache_path(store, file_root, path)
            cache_meta = {
                "root": str(file_root.resolve()),
                "relative_path": path.relative_to(file_root).as_posix(),
                "size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
            }
            file_items: list[dict[str, Any]]
            cache_hit = False
            if cache_path.exists():
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if cached.get("meta") == cache_meta:
                    file_items = list(cached.get("items", []))
                    hit_files += 1
                    cache_hit = True
                else:
                    file_items = ingest_file(root_index=root_index, root=file_root, path=path, source_name=source_name, max_chars=max_chars)
                    miss_files += 1
            else:
                file_items = ingest_file(root_index=root_index, root=file_root, path=path, source_name=source_name, max_chars=max_chars)
                miss_files += 1
            if not cache_hit:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps({"meta": cache_meta, "items": file_items}, ensure_ascii=False), encoding="utf-8")
                tmp.replace(cache_path)
            for item in file_items:
                if item["id"] not in seen_ids:
                    items.append(item)
                    seen_ids.add(item["id"])
    return items, {"hit_files": hit_files, "miss_files": miss_files, "item_count": len(items)}


def load_build_cache(store: Path) -> dict[str, Any] | None:
    path = build_cache_path(store)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_runtime_policy(store: Path) -> dict[str, Any]:
    path = runtime_policy_path(store)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_build_cache(store: Path, fingerprint: dict[str, Any], payload: dict[str, Any]) -> None:
    path = build_cache_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            {
                "schema_version": "ivy_context_memory.build_cache.v0.1",
                "updated_at": utc_now(),
                "fingerprint": fingerprint,
                "payload": payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    tmp.replace(path)


def note_to_corpus_item(note: dict[str, Any]) -> dict[str, Any]:
    text = str(note["text"]).strip()
    digest = content_hash(text)[:16]
    note_id = note.get("id") or f"note_{digest}"
    safety_label = "secret_like" if SECRET_RE.search(text) else str(note.get("safety_label", "normal"))
    exposure_policy = "forbidden" if safety_label == "secret_like" else str(note.get("exposure_policy", "frontier_ok"))
    return {
        "id": slug(note_id, 128),
        "source_family": str(note.get("source_family", "doc_memory")),
        "authority": str(note.get("authority", "medium")),
        "created_at": str(note.get("created_at", utc_now()))[:10],
        "supersedes": list(note.get("supersedes", [])),
        "tags": list(dict.fromkeys(["agent_note", *note.get("tags", [])])) or ["agent_note"],
        "text": text,
        "provenance": {
            "artifact_path": str(note.get("source_path", "root/ivy_context_memory/notes.jsonl")).replace("\\", "/"),
            "source_hash": digest,
            "generator": "plugins/ivy-context-memory/scripts/ivy_context_memory.py",
            "record_key": slug(note_id, 128),
        },
        "staleness": str(note.get("staleness", "current")),
        "conflicts_with": list(note.get("conflicts_with", [])),
        "safety_label": safety_label,
        "taint_labels": ["secret_like"] if safety_label == "secret_like" else list(note.get("taint_labels", ["normal"])),
        "exposure_policy": exposure_policy,
        "claim_type": str(note.get("claim_type", "fact")),
        "canonical_for": list(note.get("canonical_for", [slug(note_id, 120)])),
    }


def item_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("id", "")),
            str(item.get("source_family", "")),
            str(item.get("authority", "")),
            str(item.get("staleness", "")),
            " ".join(str(tag) for tag in item.get("tags", [])),
            json.dumps(item.get("provenance", {}), sort_keys=True),
            str(item.get("text", "")),
        ]
    )


def build_query_index(store: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    postings: dict[str, list[str]] = {}
    docs: dict[str, dict[str, Any]] = {}
    token_df: dict[str, int] = {}
    for item in items:
        item_id = str(item["id"])
        docs[item_id] = item
        tokens = sorted(set(tokenize(item_search_text(item))))
        for token in tokens:
            postings.setdefault(token, []).append(item_id)
            token_df[token] = token_df.get(token, 0) + 1
    payload = {
        "schema_version": "ivy_context_memory.query_index.v0.1",
        "created_at": utc_now(),
        "items": len(items),
        "tokens": len(postings),
        "docs": docs,
        "postings": postings,
        "token_df": token_df,
    }
    path = index_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    stat = path.stat()
    _QUERY_INDEX_CACHE[str(path.resolve())] = (int(stat.st_mtime_ns), int(stat.st_size), payload)
    return {"path": str(path), "items": len(items), "tokens": len(postings)}


def load_query_index(store: Path) -> dict[str, Any] | None:
    path = index_path(store)
    if not path.exists():
        return None
    stat = path.stat()
    cache_key = str(path.resolve())
    cached = _QUERY_INDEX_CACHE.get(cache_key)
    mtime_ns = int(stat.st_mtime_ns)
    size = int(stat.st_size)
    if cached and cached[0] == mtime_ns and cached[1] == size:
        return cached[2]
    payload = json.loads(path.read_text(encoding="utf-8"))
    _QUERY_INDEX_CACHE[cache_key] = (mtime_ns, size, payload)
    return payload


def raw_to_corpus_item(raw: dict[str, Any]) -> CorpusItem:
    taint_labels = derive_taint_labels(raw)
    exposure_policy = derive_exposure_policy(raw, taint_labels)
    search_text = " ".join(
        [
            raw["id"],
            split_identifier(raw["id"]),
            raw["source_family"],
            raw["authority"],
            raw.get("staleness", ""),
            " ".join(raw.get("tags", [])),
            split_identifier(" ".join(raw.get("tags", []))),
            json.dumps(raw.get("provenance", {}), sort_keys=True),
            raw["text"],
        ]
    )
    tokens = tokenize(search_text)
    return CorpusItem(
        id=raw["id"],
        source_family=raw["source_family"],
        authority=raw["authority"],
        staleness=raw.get("staleness", "unknown"),
        safety_label=raw.get("safety_label", "normal"),
        taint_labels=taint_labels,
        exposure_policy=exposure_policy,
        tags=list(raw.get("tags", [])),
        text=raw["text"],
        provenance=dict(raw.get("provenance", {})),
        conflicts_with=list(raw.get("conflicts_with", [])),
        raw=raw,
        tokens=tokens,
        token_counts=Counter(tokens),
        search_text=norm(search_text),
    )


def item_cache_key(item: dict[str, Any]) -> tuple[str, str, int]:
    provenance = item.get("provenance", {})
    return (str(item.get("id", "")), str(provenance.get("source_hash", "")), len(str(item.get("text", ""))))


def raw_items_to_corpus(items: list[dict[str, Any]]) -> list[CorpusItem]:
    converted: list[CorpusItem] = []
    for item in items:
        cache_key = item_cache_key(item)
        cached = _CORPUS_ITEM_CACHE.get(cache_key)
        if cached is None:
            cached = raw_to_corpus_item(item)
            _CORPUS_ITEM_CACHE[cache_key] = cached
        converted.append(cached)
    return converted


def checkpoint_numbers(text: str) -> set[str]:
    return set(re.findall(r"\bcp[-_ ]?(\d+)\b", text.lower()))


def prefilter_item_features(item: dict[str, Any]) -> dict[str, Any]:
    cache_key = item_cache_key(item)
    cached = _ITEM_FEATURE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    features = {
        "tags": set(str(tag).lower() for tag in item.get("tags", [])),
        "checkpoints": checkpoint_numbers(item_search_text(item)),
        "source_family": item.get("source_family"),
    }
    _ITEM_FEATURE_CACHE[cache_key] = features
    return features


def prefilter_feature_bonus(item: dict[str, Any], query_lower: str, query_checkpoints: set[str], policy: dict[str, Any]) -> float:
    weights = policy.get("prefilter_feature_weights", {}) if isinstance(policy, dict) else {}
    features = prefilter_item_features(item)
    tags = features["tags"]
    bonus = 0.0
    if "agent_note" in tags:
        bonus += float(weights.get("agent_note_boost", 500.0))
    if query_checkpoints:
        item_checkpoints = features["checkpoints"]
        if query_checkpoints & item_checkpoints:
            bonus += float(weights.get("checkpoint_match_boost", 0.0))
        elif "agent_note" in tags:
            bonus += float(weights.get("agent_note_checkpoint_mismatch_penalty", 0.0))
    if features["source_family"] == "source_code" and not any(token in query_lower for token in ["code", "function", "script", "schema", "module"]):
        bonus += float(weights.get("source_code_non_code_penalty", 0.0))
    return bonus


def select_prefilter_items(store: Path, query: str, *, max_items: int = 192, policy: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = load_query_index(store)
    if not index:
        return [], {"enabled": False, "reason": "missing_index"}
    docs: dict[str, dict[str, Any]] = index.get("docs", {})
    postings: dict[str, list[str]] = index.get("postings", {})
    token_df: dict[str, int] = index.get("token_df", {})
    query_tokens = set(tokenize(f"{query} mome moce acca context memory"))
    scores: dict[str, float] = {}
    matches: dict[str, list[str]] = {}
    total_items = max(1, int(index.get("items", len(docs) or 1)))
    for token in query_tokens:
        ids = postings.get(token, [])
        if not ids:
            continue
        weight = 1.0 + (total_items / max(1, int(token_df.get(token, len(ids)))))
        for item_id in ids:
            scores[item_id] = scores.get(item_id, 0.0) + weight
            matches.setdefault(item_id, []).append(token)
    if not scores:
        return [], {"enabled": True, "reason": "no_token_hits", "candidate_count": 0, "total_items": total_items}
    policy = policy or {}
    feature_adjustments: dict[str, float] = {}
    query_lower = query.lower()
    query_checkpoints = checkpoint_numbers(query)
    for item_id in list(scores):
        item = docs.get(item_id)
        if item is None:
            continue
        adjustment = prefilter_feature_bonus(item, query_lower, query_checkpoints, policy)
        if adjustment:
            scores[item_id] += adjustment
            feature_adjustments[item_id] = round(adjustment, 3)
    ranked = sorted(
        scores,
        key=lambda item_id: (
            scores[item_id],
            len(matches.get(item_id, [])),
            1 if docs[item_id].get("authority") in {"high", "medium"} else 0,
            len(str(docs[item_id].get("text", ""))),
        ),
        reverse=True,
    )
    selected_ids = ranked[:max_items]
    selected = [docs[item_id] for item_id in selected_ids if item_id in docs]
    return selected, {
        "enabled": True,
        "reason": "ok",
        "candidate_count": len(selected),
        "total_items": total_items,
        "max_items": max_items,
        "top_ids": selected_ids[:10],
        "feature_profile": policy.get("prefilter_feature_profile", "default") if isinstance(policy, dict) else "default",
        "top_feature_adjustments": {item_id: feature_adjustments[item_id] for item_id in selected_ids[:10] if item_id in feature_adjustments},
    }


def write_subset_dataset(store: Path, items: list[dict[str, Any]]) -> Path:
    out = query_subset_path(store)
    if out.exists():
        shutil.rmtree(out)
    (out / "corpus").mkdir(parents=True)
    (out / "eval").mkdir(parents=True)
    with (out / "corpus" / "corpus_items.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    (out / "eval" / "cases.json").write_text(
        json.dumps({"schema_version": "context_stress_eval_cases.v0.1", "cases": []}, indent=2),
        encoding="utf-8",
    )
    return out


def write_dataset(store: Path, items: list[dict[str, Any]], *, source_roots: list[str]) -> dict[str, Any]:
    out = dataset_path(store)
    if out.exists():
        shutil.rmtree(out)
    (out / "corpus").mkdir(parents=True)
    (out / "eval").mkdir(parents=True)
    (out / "metadata").mkdir(parents=True)
    corpus_path = out / "corpus" / "corpus_items.jsonl"
    with corpus_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    cases = {
        "schema_version": "context_stress_eval_cases.v0.1",
        "cases": [
            {
                "id": "live_query_placeholder",
                "category": "general",
                "query": "placeholder query for live context memory store",
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
                "notes": "Placeholder only; live queries call the router directly.",
            }
        ],
    }
    (out / "eval" / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": "context_stress_dataset_manifest.v0.1",
        "dataset_id": DEFAULT_DATASET,
        "created_at": utc_now(),
        "case_count": 1,
        "corpus_items": len(items),
        "source_roots": source_roots,
        "file_sha256": {
            "corpus": content_hash(corpus_path.read_text(encoding="utf-8")),
            "cases": content_hash((out / "eval" / "cases.json").read_text(encoding="utf-8")),
        },
        "generator": {
            "script": "plugins/ivy-context-memory/scripts/ivy_context_memory.py",
            "deterministic": True,
        },
    }
    (out / "metadata" / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    index = build_query_index(store, items)
    return {"dataset": str(out), "corpus_items": len(items), "source_roots": source_roots, "index": index}


def build_store(store: Path, *, max_files: int | None = None, extensions: set[str] | None = None) -> dict[str, Any]:
    init_store(store)
    state = load_state(store)
    roots = [Path(path) for path in state.get("source_roots", []) if Path(path).exists()]
    active_extensions = extensions or DEFAULT_EXTENSIONS
    fingerprint = source_fingerprint(store, roots, extensions=active_extensions, max_files=max_files)
    cache = load_build_cache(store)
    if (
        cache
        and cache.get("fingerprint", {}).get("fingerprint_sha256") == fingerprint["fingerprint_sha256"]
        and (dataset_path(store) / "corpus" / "corpus_items.jsonl").exists()
        and index_path(store).exists()
    ):
        cached_payload = dict(cache.get("payload", {}))
        cached_payload["cache"] = {"status": "hit", "fingerprint_path": str(build_cache_path(store))}
        state["last_build"] = {"at": utc_now(), **cached_payload}
        save_state(store, state)
        return {"ok": True, "store": str(store), **cached_payload}

    items, chunk_cache = cached_ingest(store, roots, max_chars=3600, max_files=max_files, extensions=active_extensions) if roots else ([], {"hit_files": 0, "miss_files": 0, "item_count": 0})
    note_items = [note_to_corpus_item(note) for note in read_notes(store)]
    items.extend(note_items)
    payload = write_dataset(store, items, source_roots=[str(path) for path in roots])
    payload["notes"] = len(note_items)
    payload["cache"] = {"status": "miss", "fingerprint_path": str(build_cache_path(store))}
    payload["chunk_cache"] = chunk_cache
    save_build_cache(store, fingerprint, payload)
    state["last_build"] = {"at": utc_now(), **payload}
    save_state(store, state)
    return {"ok": True, "store": str(store), **payload}


def warm_store(store: Path, *, queries: list[str] | None = None, max_prefilter_items: int | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    data = dataset_path(store)
    if not (data / "corpus" / "corpus_items.jsonl").exists() or not index_path(store).exists():
        build_store(store)
    runtime_policy = load_runtime_policy(store)
    if max_prefilter_items is None:
        max_prefilter_items = int(runtime_policy.get("max_prefilter_items", 32))
    index = load_query_index(store)
    warm_queries = [query for query in (queries or DEFAULT_WARM_QUERIES) if query.strip()]
    rows = []
    for query in warm_queries:
        query_started = time.perf_counter()
        subset_items, prefilter_meta = select_prefilter_items(store, query, max_items=max_prefilter_items, policy=runtime_policy)
        items = raw_items_to_corpus(subset_items) if subset_items else []
        rows.append(
            {
                "query": query,
                "candidate_count": len(subset_items),
                "corpus_items_warmed": len(items),
                "prefilter": prefilter_meta,
                "wall_ms": round((time.perf_counter() - query_started) * 1000, 3),
            }
        )
    return {
        "ok": True,
        "store": str(store),
        "index_loaded": bool(index),
        "index_items": int(index.get("items", 0)) if index else 0,
        "max_prefilter_items": max_prefilter_items,
        "warmed_queries": len(rows),
        "query_index_cache_entries": len(_QUERY_INDEX_CACHE),
        "item_feature_cache_entries": len(_ITEM_FEATURE_CACHE),
        "corpus_item_cache_entries": len(_CORPUS_ITEM_CACHE),
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "rows": rows,
    }


def add_source(store: Path, source_root: Path, *, build: bool) -> dict[str, Any]:
    init_store(store)
    source_root = source_root.resolve()
    if not source_root.exists():
        raise FileNotFoundError(f"source root not found: {source_root}")
    state = load_state(store)
    roots = list(dict.fromkeys([*state.get("source_roots", []), str(source_root)]))
    state["source_roots"] = roots
    save_state(store, state)
    payload = {"ok": True, "store": str(store), "source_roots": roots}
    if build:
        payload["build"] = build_store(store)
    return payload


def remember(
    store: Path,
    *,
    text: str,
    source_path: str,
    tags: list[str],
    authority: str = "medium",
    staleness: str = "current",
    supersedes: list[str] | None = None,
    conflicts_with: list[str] | None = None,
    build: bool = True,
) -> dict[str, Any]:
    init_store(store)
    if not text.strip():
        raise ValueError("memory text is empty")
    if SECRET_RE.search(text):
        raise ValueError("refusing to store obvious secret-like memory text")
    note = {
        "id": f"note_{content_hash(source_path + text)[:16]}",
        "text": text.strip(),
        "source_path": source_path,
        "tags": tags,
        "authority": authority,
        "source_family": "doc_memory",
        "staleness": staleness,
        "supersedes": supersedes or [],
        "conflicts_with": conflicts_with or [],
        "safety_label": "normal",
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
        "created_at": utc_now(),
    }
    with notes_path(store).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(note, sort_keys=True) + "\n")
    build_result = build_store(store) if build else {"ok": True, "skipped": True}
    return {"ok": True, "store": str(store), "note": note, "build": build_result}


AGENT_HOOKS = {"before_task", "before_edit", "after_test", "after_task", "remember", "supersede"}


def redact_session_text(text: str) -> str:
    return REDACT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)


def normalize_session_record(raw: dict[str, Any], index: int) -> dict[str, Any]:
    role = str(raw.get("role") or raw.get("actor") or raw.get("type") or "event").lower()
    event_type = str(raw.get("event_type") or raw.get("type") or role).lower()
    text = raw.get("text", raw.get("content", raw.get("message", "")))
    if isinstance(text, list):
        text = "\n".join(str(item) for item in text)
    record = {
        "index": index,
        "event_type": event_type,
        "role": role,
        "text": redact_session_text(str(text).strip()),
        "created_at": str(raw.get("created_at", utc_now())),
    }
    for key in ["tool", "command", "path", "status", "passed", "commit", "files", "tags"]:
        if key in raw:
            record[key] = raw[key]
    return record


def normalize_session(payload: dict[str, Any]) -> dict[str, Any]:
    raw_records = payload.get("records", payload.get("events", payload.get("messages", [])))
    if not isinstance(raw_records, list):
        raise ValueError("session payload must include records/messages/events list")
    session_id = slug(str(payload.get("session_id") or payload.get("id") or content_hash(json.dumps(raw_records, sort_keys=True))[:16]), 96)
    records = [normalize_session_record(raw if isinstance(raw, dict) else {"text": str(raw)}, idx) for idx, raw in enumerate(raw_records)]
    return {
        "schema_version": "ivy_context_memory.agent_session.v0.1",
        "session_id": session_id,
        "created_at": str(payload.get("created_at", utc_now())),
        "source": str(payload.get("source", "agent_chat")),
        "workspace": str(payload.get("workspace", "")),
        "task": redact_session_text(str(payload.get("task", "")).strip()),
        "records": records,
    }


def session_path(store: Path, session_id: str) -> Path:
    return sessions_dir(store) / f"{slug(session_id, 96)}.json"


def write_session_record(store: Path, session: dict[str, Any]) -> Path:
    init_store(store)
    path = session_path(store, str(session["session_id"]))
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def memory_delta_text(delta: dict[str, Any]) -> str:
    prefix = {
        "decision": "Decision",
        "failure": "Failure",
        "test_result": "Verification",
        "outcome": "Outcome",
        "preference": "Preference",
        "command": "Command",
    }.get(str(delta.get("delta_type")), "Memory")
    return f"{prefix}: {delta['text']}"


def derive_memory_deltas(session: dict[str, Any]) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    task = session.get("task") or session["session_id"]
    for record in session["records"]:
        text = str(record.get("text", "")).strip()
        if not text or SECRET_RE.search(text):
            continue
        event_type = str(record.get("event_type", ""))
        lower = text.lower()
        delta_type: str | None = None
        authority = "medium"
        tags = ["agent_session", f"session_{session['session_id']}"]
        if event_type in {"decision", "design_decision"} or lower.startswith("decision:"):
            delta_type = "decision"
            tags.append("decision")
            authority = "high"
        elif event_type in {"failure", "error"} or lower.startswith("failure:"):
            delta_type = "failure"
            tags.append("failure")
        elif event_type in {"test", "test_result"} or "passed" in lower or "failed" in lower:
            delta_type = "test_result"
            tags.append("verification")
            authority = "high" if bool(record.get("passed", "passed" in lower and "failed" not in lower)) else "medium"
        elif event_type in {"outcome", "final", "summary"}:
            delta_type = "outcome"
            tags.append("outcome")
            authority = "high"
        elif any(term in lower for term in ["prefer ", "always ", "never "]):
            delta_type = "preference"
            tags.append("preference")
        elif event_type in {"tool", "command"} and record.get("command"):
            delta_type = "command"
            tags.append("command")
            text = f"{record.get('command')}: {text}"
        if delta_type is None:
            continue
        delta = {
            "schema_version": "ivy_context_memory.memory_delta.v0.1",
            "id": f"delta_{content_hash(session['session_id'] + str(record['index']) + text)[:16]}",
            "session_id": session["session_id"],
            "delta_type": delta_type,
            "text": redact_session_text(text),
            "source_path": f"root/ivy_context_memory/sessions/{session['session_id']}.json#{record['index']}",
            "tags": tags,
            "authority": authority,
            "task": task,
            "created_at": utc_now(),
        }
        deltas.append(delta)
    return deltas


def append_memory_deltas(store: Path, deltas: list[dict[str, Any]]) -> None:
    if not deltas:
        return
    with deltas_path(store).open("a", encoding="utf-8", newline="\n") as handle:
        for delta in deltas:
            handle.write(json.dumps(delta, sort_keys=True) + "\n")


def ingest_session(store: Path, payload: dict[str, Any], *, remember_deltas: bool = True, build: bool = True) -> dict[str, Any]:
    session = normalize_session(payload)
    path = write_session_record(store, session)
    deltas = derive_memory_deltas(session)
    append_memory_deltas(store, deltas)
    notes: list[dict[str, Any]] = []
    if remember_deltas:
        for delta in deltas:
            result = remember(
                store,
                text=memory_delta_text(delta),
                source_path=str(delta["source_path"]),
                tags=list(delta["tags"]),
                authority=str(delta["authority"]),
                build=build,
            )
            notes.append(result["note"])
    elif build:
        build_store(store)
    return {
        "ok": True,
        "store": str(store),
        "session": session,
        "session_path": str(path),
        "deltas": deltas,
        "delta_count": len(deltas),
        "remembered_notes": len(notes),
    }


def agent_memory_policy() -> dict[str, Any]:
    return {
        "schema_version": "ivy_context_memory.agent_policy.v0.1",
        "precedence": ["system/developer/user instructions", "current repo state", "verified memory", "unverified traces"],
        "before_task": "query memory for relevant decisions, failures, and current constraints before planning substantial work",
        "before_edit": "query memory for file/module-specific context before editing unfamiliar areas",
        "after_test": "remember verified test outcomes and failures with commands when useful",
        "after_task": "write concise memory deltas for durable decisions, outcomes, stale facts, and follow-ups",
        "safety": "memory is advisory; never store secrets; abstain when evidence is missing or stale",
    }


def context_packet_v2(store: Path, *, query: str, hook: str = "before_task") -> dict[str, Any]:
    result = query_store(store, query=query)
    return {
        "ok": True,
        "schema_version": "ivy_context_memory.context_packet.v0.2",
        "hook": hook,
        "query": query,
        "policy": agent_memory_policy(),
        "packet": {
            "mode": result["packet_mode"],
            "text": result["packet_text"],
            "selected_ids": result["selected_ids"],
            "decision": result["decision"],
            "answerability": result["answerability"],
            "route_proof": result["route_proof"],
        },
        "timings_ms": result["timings_ms"],
        "packet_path": result["packet_path"],
    }


def agent_hook(store: Path, *, hook: str, task: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    hook = hook.strip().lower()
    if hook not in AGENT_HOOKS:
        raise ValueError(f"unknown agent hook: {hook}")
    payload = payload or {}
    if hook in {"before_task", "before_edit"}:
        query = task or str(payload.get("query", payload.get("task", "")))
        return context_packet_v2(store, query=query, hook=hook)
    if hook in {"after_task", "after_test"}:
        session_payload = {
            "session_id": payload.get("session_id", f"{hook}_{content_hash(task + utc_now())[:10]}"),
            "source": payload.get("source", "agent_hook"),
            "workspace": payload.get("workspace", ""),
            "task": task or payload.get("task", ""),
            "records": payload.get("records", []),
        }
        return ingest_session(store, session_payload, remember_deltas=True, build=True)
    if hook == "remember":
        return remember(
            store,
            text=str(payload.get("text", task)),
            source_path=str(payload.get("source_path", "root/ivy_context_memory/agent_hook")),
            tags=[str(tag) for tag in payload.get("tags", ["agent_hook"])],
            authority=str(payload.get("authority", "medium")),
            staleness=str(payload.get("staleness", "current")),
            supersedes=[str(item) for item in payload.get("supersedes", [])],
        )
    if hook == "supersede":
        return remember(
            store,
            text=str(payload.get("text", task)),
            source_path=str(payload.get("source_path", "root/ivy_context_memory/agent_hook_supersede")),
            tags=[str(tag) for tag in payload.get("tags", ["agent_hook", "supersede"])],
            authority=str(payload.get("authority", "high")),
            supersedes=[str(item) for item in payload.get("supersedes", [])],
        )
    raise AssertionError("unreachable")


def auto_variant(result: Any) -> str:
    packet_mode = result.frontier_packet.get("packet_mode")
    if packet_mode in {"compact_default", "proof_lite", "contradiction_aware"}:
        return str(packet_mode)
    proof = result.route_proof
    if proof.get("conflict_pairs") or proof.get("exposure_summary", {}).get("masked_selected", 0):
        return "contradiction_aware"
    if any(row.get("reason") in {"decoy_not_admissible_as_authority", "stale_not_requested"} for row in proof.get("rejected_evidence", [])):
        return "contradiction_aware"
    if len(result.selected_ids) > 1:
        return "proof_lite"
    return "compact_default"


def query_store(
    store: Path,
    *,
    query: str,
    variant: str = "auto",
    top_k: int = 5,
    prefilter: bool = True,
    max_prefilter_items: int | None = None,
) -> dict[str, Any]:
    query_started = time.perf_counter()
    data = dataset_path(store)
    if not (data / "corpus" / "corpus_items.jsonl").exists():
        build_store(store)
    runtime_policy = load_runtime_policy(store)
    if max_prefilter_items is None:
        max_prefilter_items = int(runtime_policy.get("max_prefilter_items", 32))
    router_candidate_k = int(runtime_policy.get("router_candidate_k", 16))
    router_candidate_k = max(1, min(router_candidate_k, max_prefilter_items))
    prefilter_meta: dict[str, Any] = {"enabled": False, "reason": "disabled"}
    route_dataset = data
    prefilter_started = time.perf_counter()
    if prefilter:
        subset_items, prefilter_meta = select_prefilter_items(store, query, max_items=max_prefilter_items, policy=runtime_policy)
        prefilter_ms = (time.perf_counter() - prefilter_started) * 1000
        corpus_started = time.perf_counter()
        if subset_items:
            items = raw_items_to_corpus(subset_items)
        else:
            items = load_corpus(data)
        corpus_ms = (time.perf_counter() - corpus_started) * 1000
    else:
        prefilter_ms = (time.perf_counter() - prefilter_started) * 1000
        corpus_started = time.perf_counter()
        items = load_corpus(data)
        corpus_ms = (time.perf_counter() - corpus_started) * 1000
    router_started = time.perf_counter()
    router = MoMEMoCERouter(items, candidate_backend="indexed", dataset_path=route_dataset, top_k=top_k, candidate_k=router_candidate_k)
    router_init_ms = (time.perf_counter() - router_started) * 1000
    started = time.perf_counter()
    result = router.route(query)
    if not result.selected_ids and items:
        retry = router.route(f"mome context memory query: {query}")
        if retry.selected_ids:
            result = retry
            result.query = query
            result.route_proof["query"] = query
            result.frontier_packet["query"] = query
    latency_ms = (time.perf_counter() - started) * 1000
    case = {
        "id": "live_query",
        "category": "general",
        "query": query,
        "required_source_ids": [],
        "forbidden_source_ids": [],
        "must_abstain": result.decision != "context_packet_ready",
        "requires_conflict_resolution": bool(result.route_proof.get("conflict_pairs")),
        "requires_safety_priority": bool(result.route_proof.get("exposure_summary", {}).get("masked_selected", 0)),
    }
    render_started = time.perf_counter()
    chosen_variant = auto_variant(result) if variant == "auto" else variant
    packet_text = render_variant(chosen_variant, case=case, result=result)
    render_ms = (time.perf_counter() - render_started) * 1000
    packet_record = {
        "created_at": utc_now(),
        "query": query,
        "variant": chosen_variant,
        "selected_ids": result.selected_ids,
        "decision": result.decision,
        "latency_ms": round(latency_ms, 3),
        "packet_text": packet_text,
    }
    packet_hash = content_hash(json.dumps(packet_record, sort_keys=True))[:16]
    packet_path = store / "packets" / f"{packet_hash}.json"
    packet_write_started = time.perf_counter()
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet_record, ensure_ascii=False, indent=2), encoding="utf-8")
    packet_write_ms = (time.perf_counter() - packet_write_started) * 1000
    total_wall_ms = (time.perf_counter() - query_started) * 1000
    timings_ms = {
        "prefilter": round(prefilter_ms, 3),
        "corpus": round(corpus_ms, 3),
        "router_init": round(router_init_ms, 3),
        "route": round(latency_ms, 3),
        "render": round(render_ms, 3),
        "packet_write": round(packet_write_ms, 3),
        "total": round(total_wall_ms, 3),
    }
    return {
        "ok": True,
        "store": str(store),
        "dataset": str(data),
        "route_dataset": str(route_dataset),
        "query": query,
        "variant": chosen_variant,
        "packet_mode": result.frontier_packet.get("packet_mode", chosen_variant),
        "decision": result.decision,
        "answerability": result.frontier_packet.get("answerability"),
        "selected_ids": result.selected_ids,
        "selected_count": len(result.selected_ids),
        "latency_ms": round(latency_ms, 3),
        "wall_ms": round(total_wall_ms, 3),
        "timings_ms": timings_ms,
        "prefilter": prefilter_meta,
        "router_candidate_k": router_candidate_k,
        "packet_words": rough_tokens(packet_text),
        "packet_text": packet_text,
        "route_proof": result.route_proof,
        "packet_path": str(packet_path),
    }


def status(store: Path) -> dict[str, Any]:
    init_store(store)
    state = load_state(store)
    data = dataset_path(store)
    index = load_query_index(store)
    build_cache = load_build_cache(store)
    corpus_items = 0
    if (data / "corpus" / "corpus_items.jsonl").exists():
        corpus_items = sum(1 for line in (data / "corpus" / "corpus_items.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "ok": True,
        "store": str(store),
        "dataset": str(data),
        "source_roots": state.get("source_roots", []),
        "notes": len(read_notes(store)),
        "sessions": len(list(sessions_dir(store).glob("*.json"))) if sessions_dir(store).exists() else 0,
        "memory_deltas": sum(1 for line in deltas_path(store).read_text(encoding="utf-8").splitlines() if line.strip()) if deltas_path(store).exists() else 0,
        "corpus_items": corpus_items,
        "index": {
            "items": index.get("items", 0) if index else 0,
            "tokens": index.get("tokens", 0) if index else 0,
            "path": str(index_path(store)),
            "exists": bool(index),
        },
        "build_cache": {
            "exists": bool(build_cache),
            "path": str(build_cache_path(store)),
            "updated_at": build_cache.get("updated_at") if build_cache else None,
            "fingerprint_sha256": build_cache.get("fingerprint", {}).get("fingerprint_sha256") if build_cache else None,
            "file_count": build_cache.get("fingerprint", {}).get("file_count") if build_cache else 0,
        },
        "runtime_policy": {
            "path": str(runtime_policy_path(store)),
            "exists": runtime_policy_path(store).exists(),
            "policy": load_runtime_policy(store),
        },
        "process_caches": {
            "query_index_cache_entries": len(_QUERY_INDEX_CACHE),
            "item_feature_cache_entries": len(_ITEM_FEATURE_CACHE),
            "corpus_item_cache_entries": len(_CORPUS_ITEM_CACHE),
        },
        "last_build": state.get("last_build"),
    }


class ApiHandler(BaseHTTPRequestHandler):
    store: Path = DEFAULT_STORE

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/health":
                self._send(200, {"ok": True, "service": "ivy-context-memory", "store": str(self.store)})
            elif self.path == "/status":
                self._send(200, status(self.store))
            else:
                self._send(404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            self._send(500, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/query":
                self._send(
                    200,
                    query_store(
                        self.store,
                        query=str(payload["query"]),
                        variant=str(payload.get("variant", "auto")),
                        prefilter=bool(payload.get("prefilter", True)),
                        max_prefilter_items=int(payload["max_prefilter_items"]) if "max_prefilter_items" in payload else None,
                    ),
                )
            elif self.path == "/remember":
                self._send(
                    200,
                    remember(
                        self.store,
                        text=str(payload["text"]),
                        source_path=str(payload.get("source_path", "root/ivy_context_memory/api_note")),
                        tags=[str(tag) for tag in payload.get("tags", [])],
                        authority=str(payload.get("authority", "medium")),
                        staleness=str(payload.get("staleness", "current")),
                        supersedes=[str(item) for item in payload.get("supersedes", [])],
                        conflicts_with=[str(item) for item in payload.get("conflicts_with", [])],
                        build=bool(payload.get("build", True)),
                    ),
                )
            elif self.path == "/session/ingest":
                self._send(
                    200,
                    ingest_session(
                        self.store,
                        payload,
                        remember_deltas=bool(payload.get("remember_deltas", True)),
                        build=bool(payload.get("build", True)),
                    ),
                )
            elif self.path == "/agent/hook":
                self._send(
                    200,
                    agent_hook(
                        self.store,
                        hook=str(payload["hook"]),
                        task=str(payload.get("task", "")),
                        payload=dict(payload.get("payload", {})) if isinstance(payload.get("payload", {}), dict) else {},
                    ),
                )
            elif self.path == "/packet/v2":
                self._send(200, context_packet_v2(self.store, query=str(payload["query"]), hook=str(payload.get("hook", "before_task"))))
            elif self.path == "/ingest":
                self._send(200, add_source(self.store, Path(str(payload["source_root"])), build=bool(payload.get("build", True))))
            elif self.path == "/build":
                self._send(200, build_store(self.store))
            elif self.path == "/warm":
                queries = payload.get("queries")
                if queries is not None and not isinstance(queries, list):
                    queries = [str(queries)]
                self._send(
                    200,
                    warm_store(
                        self.store,
                        queries=[str(query) for query in queries] if isinstance(queries, list) else None,
                        max_prefilter_items=int(payload["max_prefilter_items"]) if "max_prefilter_items" in payload else None,
                    ),
                )
            else:
                self._send(404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            self._send(400, {"ok": False, "error": str(exc)})


def serve(store: Path, *, host: str, port: int) -> dict[str, Any]:
    init_store(store)
    ApiHandler.store = store
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(json.dumps({"ok": True, "service": "ivy-context-memory", "url": f"http://{host}:{port}", "store": str(store)}, indent=2), flush=True)
    server.serve_forever()
    return {"ok": True}


def print_payload(payload: dict[str, Any], *, text: bool = False) -> None:
    if text:
        print(payload.get("packet_text", json.dumps(payload, ensure_ascii=False, indent=2)))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def mcp_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "ivy_memory_query",
            "description": "Query IVY context memory and return an ACCA packet plus route proof.",
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "variant": {"type": "string", "enum": ["auto", "compact_default", "proof_lite", "contradiction_aware"]},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                    "prefilter": {"type": "boolean"},
                    "max_prefilter_items": {"type": "integer", "minimum": 1, "maximum": 2048},
                },
            },
        },
        {
            "name": "ivy_memory_remember",
            "description": "Store a short safe verified memory note and rebuild the live memory dataset.",
            "inputSchema": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {"type": "string", "minLength": 1},
                    "source_path": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "authority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "staleness": {"type": "string", "enum": ["current", "stale"]},
                    "supersedes": {"type": "array", "items": {"type": "string"}},
                    "conflicts_with": {"type": "array", "items": {"type": "string"}},
                    "build": {"type": "boolean"},
                },
            },
        },
        {
            "name": "ivy_memory_session_ingest",
            "description": "Ingest a Codex/OpenCode chat/session transcript, derive memory deltas, and optionally remember them.",
            "inputSchema": {
                "type": "object",
                "required": ["records"],
                "properties": {
                    "session_id": {"type": "string"},
                    "source": {"type": "string"},
                    "workspace": {"type": "string"},
                    "task": {"type": "string"},
                    "records": {"type": "array", "items": {"type": "object"}},
                    "remember_deltas": {"type": "boolean"},
                    "build": {"type": "boolean"},
                },
            },
        },
        {
            "name": "ivy_memory_agent_hook",
            "description": "Run a Codex/OpenCode memory hook: before_task, before_edit, after_test, after_task, remember, or supersede.",
            "inputSchema": {
                "type": "object",
                "required": ["hook"],
                "properties": {
                    "hook": {"type": "string", "enum": sorted(AGENT_HOOKS)},
                    "task": {"type": "string"},
                    "payload": {"type": "object"},
                },
            },
        },
        {
            "name": "ivy_memory_ingest",
            "description": "Register a source root and optionally rebuild the live memory dataset.",
            "inputSchema": {
                "type": "object",
                "required": ["source_root"],
                "properties": {
                    "source_root": {"type": "string", "minLength": 1},
                    "build": {"type": "boolean"},
                },
            },
        },
        {
            "name": "ivy_memory_build",
            "description": "Rebuild, or cache-hit, the live memory dataset and query index.",
            "inputSchema": {"type": "object", "properties": {"max_files": {"type": "integer", "minimum": 1}}},
        },
        {
            "name": "ivy_memory_warm",
            "description": "Preload the query index and warm prefilter feature/item caches before a task.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "queries": {"type": "array", "items": {"type": "string"}},
                    "max_prefilter_items": {"type": "integer", "minimum": 1, "maximum": 2048},
                },
            },
        },
        {
            "name": "ivy_memory_status",
            "description": "Return store, dataset, index, source root, and cache status.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def mcp_resource_definitions(store: Path) -> list[dict[str, Any]]:
    latest_packet = latest_packet_path(store)
    resources = [
        {
            "uri": "ivy-memory://status",
            "name": "IVY memory status",
            "description": "Current store, dataset, query index, and build-cache status.",
            "mimeType": "application/json",
        },
        {
            "uri": "ivy-memory://latest-packet",
            "name": "Latest IVY memory packet",
            "description": "Most recent packet emitted by ivy_memory_query.",
            "mimeType": "application/json",
        },
        {
            "uri": "ivy-memory://track-record",
            "name": "IVY context memory supercharge track record",
            "description": "Checkpoint ledger, benchmark results, bugs found, and next work.",
            "mimeType": "text/markdown",
        },
    ]
    if latest_packet and latest_packet.exists():
        resources[1]["size"] = latest_packet.stat().st_size
    return resources


def mcp_prompt_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "query_ivy_memory_before_task",
            "description": "Prepare an agent to query IVY memory before starting a substantial task.",
            "arguments": [
                {
                    "name": "task",
                    "description": "The user task or technical question to ground with memory.",
                    "required": True,
                }
            ],
        },
        {
            "name": "remember_verified_milestone",
            "description": "Prepare an agent to write a short verified milestone note after tests or verification pass.",
            "arguments": [
                {
                    "name": "milestone",
                    "description": "The verified result to remember.",
                    "required": True,
                }
            ],
        },
    ]


def mcp_get_prompt(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "query_ivy_memory_before_task":
        task = str(args.get("task", "")).strip()
        return {
            "description": "Query IVY context memory before starting work.",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Before working, call `ivy_memory_query` with this task. "
                            "Read the returned packet as advisory context only; user/system/developer instructions and repo state still outrank memory.\n\n"
                            f"Task: {task}"
                        ),
                    },
                }
            ],
        }
    if name == "remember_verified_milestone":
        milestone = str(args.get("milestone", "")).strip()
        return {
            "description": "Remember a verified IVY milestone.",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "After verification, call `ivy_memory_remember` with a short factual note. "
                            "Do not store secrets, credentials, private file contents, or unverified claims.\n\n"
                            f"Milestone: {milestone}"
                        ),
                    },
                }
            ],
        }
    raise ValueError(f"unknown MCP prompt: {name}")


def latest_packet_path(store: Path) -> Path | None:
    packet_dir = store / "packets"
    if not packet_dir.exists():
        return None
    packets = sorted(packet_dir.glob("*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return packets[0] if packets else None


def mcp_read_resource(store: Path, uri: str) -> dict[str, Any]:
    if uri == "ivy-memory://status":
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(status(store), ensure_ascii=False, indent=2),
                }
            ]
        }
    if uri == "ivy-memory://latest-packet":
        path = latest_packet_path(store)
        text = path.read_text(encoding="utf-8") if path else json.dumps({"ok": False, "error": "no packets yet"}, indent=2)
        return {"contents": [{"uri": uri, "mimeType": "application/json", "text": text}]}
    if uri == "ivy-memory://track-record":
        path = REPO_ROOT / "MoME-MoCE-Exp" / "docs" / "PLUGIN_SUPERCHARGE_TRACK_RECORD_2026-05-11.md"
        text = path.read_text(encoding="utf-8") if path.exists() else "Track record document is not present in this checkout."
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}
    raise ValueError(f"unknown MCP resource: {uri}")


def mcp_call_tool(store: Path, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "ivy_memory_query":
        return query_store(
            store,
            query=str(args["query"]),
            variant=str(args.get("variant", "auto")),
            top_k=int(args.get("top_k", 5)),
            prefilter=bool(args.get("prefilter", True)),
            max_prefilter_items=int(args["max_prefilter_items"]) if "max_prefilter_items" in args else None,
        )
    if name == "ivy_memory_remember":
        tags = args.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]
        return remember(
            store,
            text=str(args["text"]),
            source_path=str(args.get("source_path", "root/ivy_context_memory/mcp_note")),
            tags=[str(tag) for tag in tags],
            authority=str(args.get("authority", "medium")),
            staleness=str(args.get("staleness", "current")),
            supersedes=[str(item) for item in args.get("supersedes", [])] if isinstance(args.get("supersedes", []), list) else [],
            conflicts_with=[str(item) for item in args.get("conflicts_with", [])] if isinstance(args.get("conflicts_with", []), list) else [],
            build=bool(args.get("build", True)),
        )
    if name == "ivy_memory_session_ingest":
        return ingest_session(
            store,
            args,
            remember_deltas=bool(args.get("remember_deltas", True)),
            build=bool(args.get("build", True)),
        )
    if name == "ivy_memory_agent_hook":
        payload = args.get("payload", {})
        return agent_hook(
            store,
            hook=str(args["hook"]),
            task=str(args.get("task", "")),
            payload=payload if isinstance(payload, dict) else {},
        )
    if name == "ivy_memory_ingest":
        return add_source(store, Path(str(args["source_root"])), build=bool(args.get("build", True)))
    if name == "ivy_memory_build":
        max_files = args.get("max_files")
        return build_store(store, max_files=int(max_files) if max_files is not None else None)
    if name == "ivy_memory_warm":
        queries = args.get("queries")
        if queries is not None and not isinstance(queries, list):
            queries = [str(queries)]
        return warm_store(
            store,
            queries=[str(query) for query in queries] if isinstance(queries, list) else None,
            max_prefilter_items=int(args["max_prefilter_items"]) if "max_prefilter_items" in args else None,
        )
    if name == "ivy_memory_status":
        return status(store)
    raise ValueError(f"unknown MCP tool: {name}")


def mcp_success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def read_mcp_message(stream: BufferedReader) -> dict[str, Any] | None:
    first = stream.readline()
    if not first:
        return None
    if first.lstrip().startswith(b"{"):
        return json.loads(first.decode("utf-8"))
    headers: dict[str, str] = {}
    line = first
    while line not in {b"\r\n", b"\n", b""}:
        raw = line.decode("ascii", errors="ignore")
        if ":" in raw:
            key, value = raw.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        line = stream.readline()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(stream.read(length).decode("utf-8"))


def write_mcp_message(stream: BufferedWriter, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    stream.flush()


def mcp_stdio(store: Path) -> None:
    init_store(store)
    reader = sys.stdin.buffer
    writer = sys.stdout.buffer
    while True:
        try:
            message = read_mcp_message(reader)
        except Exception as exc:
            write_mcp_message(writer, mcp_error(None, -32700, f"parse error: {exc}"))
            continue
        if message is None:
            return
        request_id = message.get("id")
        method = message.get("method")
        if request_id is None and str(method).startswith("notifications/"):
            continue
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {"name": "ivy-context-memory", "version": "0.1.0"},
                }
                write_mcp_message(writer, mcp_success(request_id, result))
            elif method == "tools/list":
                write_mcp_message(writer, mcp_success(request_id, {"tools": mcp_tool_definitions()}))
            elif method == "resources/list":
                write_mcp_message(writer, mcp_success(request_id, {"resources": mcp_resource_definitions(store)}))
            elif method == "resources/read":
                params = message.get("params", {})
                write_mcp_message(writer, mcp_success(request_id, mcp_read_resource(store, str(params.get("uri", "")))))
            elif method == "prompts/list":
                write_mcp_message(writer, mcp_success(request_id, {"prompts": mcp_prompt_definitions()}))
            elif method == "prompts/get":
                params = message.get("params", {})
                args = params.get("arguments") or {}
                if not isinstance(args, dict):
                    args = {}
                write_mcp_message(writer, mcp_success(request_id, mcp_get_prompt(str(params.get("name", "")), args)))
            elif method == "tools/call":
                params = message.get("params", {})
                tool_name = str(params.get("name", ""))
                args = params.get("arguments") or {}
                if not isinstance(args, dict):
                    args = {}
                try:
                    payload = mcp_call_tool(store, tool_name, args)
                    result = {
                        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                        "structuredContent": payload,
                        "isError": False,
                    }
                except Exception as exc:
                    error_payload = {"ok": False, "error": str(exc), "tool": tool_name}
                    result = {
                        "content": [{"type": "text", "text": json.dumps(error_payload, ensure_ascii=False, indent=2)}],
                        "structuredContent": error_payload,
                        "isError": True,
                    }
                write_mcp_message(writer, mcp_success(request_id, result))
            else:
                write_mcp_message(writer, mcp_error(request_id, -32601, f"method not found: {method}"))
        except Exception as exc:
            write_mcp_message(writer, mcp_error(request_id, -32603, str(exc)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IVY unlimited context/memory sidecar for Codex and OpenCode.")
    parser.add_argument("--store", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("status")

    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("--source-root", type=Path, required=True)
    ingest_parser.add_argument("--no-build", action="store_true")

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--max-files", type=int, default=None)

    warm_parser = sub.add_parser("warm")
    warm_parser.add_argument("--query", action="append", default=[])
    warm_parser.add_argument("--max-prefilter-items", type=int, default=None)

    remember_parser = sub.add_parser("remember")
    remember_parser.add_argument("--text", required=True)
    remember_parser.add_argument("--source-path", default="root/ivy_context_memory/manual_note")
    remember_parser.add_argument("--tag", action="append", default=[])
    remember_parser.add_argument("--authority", choices=["high", "medium", "low"], default="medium")
    remember_parser.add_argument("--staleness", choices=["current", "stale"], default="current")
    remember_parser.add_argument("--supersedes", action="append", default=[])
    remember_parser.add_argument("--conflicts-with", action="append", default=[])
    remember_parser.add_argument("--no-build", action="store_true")

    session_parser = sub.add_parser("session-ingest")
    session_parser.add_argument("--json", type=Path, required=True)
    session_parser.add_argument("--no-remember-deltas", action="store_true")
    session_parser.add_argument("--no-build", action="store_true")

    hook_parser = sub.add_parser("agent-hook")
    hook_parser.add_argument("--hook", choices=sorted(AGENT_HOOKS), required=True)
    hook_parser.add_argument("--task", default="")
    hook_parser.add_argument("--payload-json", type=Path, default=None)

    packet_parser = sub.add_parser("packet-v2")
    packet_parser.add_argument("--query", required=True)
    packet_parser.add_argument("--hook", default="before_task")

    query_parser = sub.add_parser("query")
    query_parser.add_argument("--query", required=True)
    query_parser.add_argument("--variant", choices=["auto", "compact_default", "proof_lite", "contradiction_aware"], default="auto")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--text", action="store_true")
    query_parser.add_argument("--no-prefilter", action="store_true")
    query_parser.add_argument("--max-prefilter-items", type=int, default=None)

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8768)
    serve_parser.add_argument("--stdio-mcp-placeholder", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("mcp")

    args = parser.parse_args(argv)
    store = resolve_store(args.store)
    try:
        if args.command == "init":
            print_payload(init_store(store))
        elif args.command == "status":
            print_payload(status(store))
        elif args.command == "ingest":
            print_payload(add_source(store, args.source_root, build=not args.no_build))
        elif args.command == "build":
            print_payload(build_store(store, max_files=args.max_files))
        elif args.command == "warm":
            print_payload(warm_store(store, queries=args.query or None, max_prefilter_items=args.max_prefilter_items))
        elif args.command == "remember":
            print_payload(
                remember(
                    store,
                    text=args.text,
                    source_path=args.source_path,
                    tags=args.tag,
                    authority=args.authority,
                    staleness=args.staleness,
                    supersedes=args.supersedes,
                    conflicts_with=args.conflicts_with,
                    build=not args.no_build,
                )
            )
        elif args.command == "session-ingest":
            payload = json.loads(args.json.read_text(encoding="utf-8"))
            print_payload(
                ingest_session(
                    store,
                    payload,
                    remember_deltas=not args.no_remember_deltas,
                    build=not args.no_build,
                )
            )
        elif args.command == "agent-hook":
            payload = json.loads(args.payload_json.read_text(encoding="utf-8")) if args.payload_json else {}
            print_payload(agent_hook(store, hook=args.hook, task=args.task, payload=payload))
        elif args.command == "packet-v2":
            print_payload(context_packet_v2(store, query=args.query, hook=args.hook))
        elif args.command == "query":
            print_payload(
                query_store(
                    store,
                    query=args.query,
                    variant=args.variant,
                    top_k=args.top_k,
                    prefilter=not args.no_prefilter,
                    max_prefilter_items=args.max_prefilter_items,
                ),
                text=args.text,
            )
        elif args.command == "serve":
            if args.stdio_mcp_placeholder:
                print(json.dumps({"ok": False, "error": "MCP protocol server is not implemented yet; use HTTP serve or CLI commands."}))
                return 2
            serve(store, host=args.host, port=args.port)
        elif args.command == "mcp":
            mcp_stdio(store)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
