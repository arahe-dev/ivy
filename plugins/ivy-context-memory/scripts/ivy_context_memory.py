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

if str(MOME_ROOT) not in sys.path:
    sys.path.insert(0, str(MOME_ROOT))
if str(MOME_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MOME_ROOT / "scripts"))

try:
    from scripts.ingest_external_corpus import DEFAULT_EXTENSIONS, SKIP_DIRS, ingest  # type: ignore  # noqa: E402
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
    from ingest_external_corpus import DEFAULT_EXTENSIONS, SKIP_DIRS, ingest  # type: ignore  # noqa: E402
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


def dataset_path(store: Path) -> Path:
    return store / "datasets" / DEFAULT_DATASET


def index_path(store: Path) -> Path:
    return store / "index" / "corpus_index.json"


def query_subset_path(store: Path) -> Path:
    return store / "query_subset"


def build_cache_path(store: Path) -> Path:
    return store / "cache" / "build_fingerprint.json"


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
    (store / "cache").mkdir(parents=True, exist_ok=True)
    state = load_state(store)
    save_state(store, state)
    notes_path(store).touch(exist_ok=True)
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


def load_build_cache(store: Path) -> dict[str, Any] | None:
    path = build_cache_path(store)
    if not path.exists():
        return None
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
    return {"path": str(path), "items": len(items), "tokens": len(postings)}


def load_query_index(store: Path) -> dict[str, Any] | None:
    path = index_path(store)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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


def raw_items_to_corpus(items: list[dict[str, Any]]) -> list[CorpusItem]:
    return [raw_to_corpus_item(item) for item in items]


def select_prefilter_items(store: Path, query: str, *, max_items: int = 192) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
    for item_id, item in docs.items():
        tags = set(str(tag) for tag in item.get("tags", []))
        if "agent_note" in tags and item_id in scores:
            scores[item_id] += 500.0
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

    items = ingest(roots, max_chars=3600, max_files=max_files, extensions=active_extensions) if roots else []
    note_items = [note_to_corpus_item(note) for note in read_notes(store)]
    items.extend(note_items)
    payload = write_dataset(store, items, source_roots=[str(path) for path in roots])
    payload["notes"] = len(note_items)
    payload["cache"] = {"status": "miss", "fingerprint_path": str(build_cache_path(store))}
    save_build_cache(store, fingerprint, payload)
    state["last_build"] = {"at": utc_now(), **payload}
    save_state(store, state)
    return {"ok": True, "store": str(store), **payload}


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


def remember(store: Path, *, text: str, source_path: str, tags: list[str], authority: str = "medium") -> dict[str, Any]:
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
        "staleness": "current",
        "safety_label": "normal",
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
        "created_at": utc_now(),
    }
    with notes_path(store).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(note, sort_keys=True) + "\n")
    build = build_store(store)
    return {"ok": True, "store": str(store), "note": note, "build": build}


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
    max_prefilter_items: int = 192,
) -> dict[str, Any]:
    data = dataset_path(store)
    if not (data / "corpus" / "corpus_items.jsonl").exists():
        build_store(store)
    prefilter_meta: dict[str, Any] = {"enabled": False, "reason": "disabled"}
    route_dataset = data
    if prefilter:
        subset_items, prefilter_meta = select_prefilter_items(store, query, max_items=max_prefilter_items)
        if subset_items:
            items = raw_items_to_corpus(subset_items)
        else:
            items = load_corpus(data)
    else:
        items = load_corpus(data)
    router = MoMEMoCERouter(items, candidate_backend="indexed", dataset_path=route_dataset, top_k=top_k)
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
    chosen_variant = auto_variant(result) if variant == "auto" else variant
    packet_text = render_variant(chosen_variant, case=case, result=result)
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
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet_record, ensure_ascii=False, indent=2), encoding="utf-8")
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
        "prefilter": prefilter_meta,
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
                        max_prefilter_items=int(payload.get("max_prefilter_items", 192)),
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
                    ),
                )
            elif self.path == "/ingest":
                self._send(200, add_source(self.store, Path(str(payload["source_root"])), build=bool(payload.get("build", True))))
            elif self.path == "/build":
                self._send(200, build_store(self.store))
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
            "name": "ivy_memory_status",
            "description": "Return store, dataset, index, source root, and cache status.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def mcp_call_tool(store: Path, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "ivy_memory_query":
        return query_store(
            store,
            query=str(args["query"]),
            variant=str(args.get("variant", "auto")),
            top_k=int(args.get("top_k", 5)),
            prefilter=bool(args.get("prefilter", True)),
            max_prefilter_items=int(args.get("max_prefilter_items", 192)),
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
        )
    if name == "ivy_memory_ingest":
        return add_source(store, Path(str(args["source_root"])), build=bool(args.get("build", True)))
    if name == "ivy_memory_build":
        max_files = args.get("max_files")
        return build_store(store, max_files=int(max_files) if max_files is not None else None)
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
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "ivy-context-memory", "version": "0.1.0"},
                }
                write_mcp_message(writer, mcp_success(request_id, result))
            elif method == "tools/list":
                write_mcp_message(writer, mcp_success(request_id, {"tools": mcp_tool_definitions()}))
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

    remember_parser = sub.add_parser("remember")
    remember_parser.add_argument("--text", required=True)
    remember_parser.add_argument("--source-path", default="root/ivy_context_memory/manual_note")
    remember_parser.add_argument("--tag", action="append", default=[])
    remember_parser.add_argument("--authority", choices=["high", "medium", "low"], default="medium")

    query_parser = sub.add_parser("query")
    query_parser.add_argument("--query", required=True)
    query_parser.add_argument("--variant", choices=["auto", "compact_default", "proof_lite", "contradiction_aware"], default="auto")
    query_parser.add_argument("--top-k", type=int, default=5)
    query_parser.add_argument("--text", action="store_true")
    query_parser.add_argument("--no-prefilter", action="store_true")
    query_parser.add_argument("--max-prefilter-items", type=int, default=192)

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
        elif args.command == "remember":
            print_payload(remember(store, text=args.text, source_path=args.source_path, tags=args.tag, authority=args.authority))
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
