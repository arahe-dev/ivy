from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    from scripts.ingest_external_corpus import DEFAULT_EXTENSIONS, ingest  # type: ignore  # noqa: E402
    from scripts.mome_moce_harness import MoMEMoCERouter, load_corpus, rough_tokens  # type: ignore  # noqa: E402
    from scripts.run_packet_format_ab import render_variant  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    from ingest_external_corpus import DEFAULT_EXTENSIONS, ingest  # type: ignore  # noqa: E402
    from mome_moce_harness import MoMEMoCERouter, load_corpus, rough_tokens  # type: ignore  # noqa: E402
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
    return {"dataset": str(out), "corpus_items": len(items), "source_roots": source_roots}


def build_store(store: Path, *, max_files: int | None = None, extensions: set[str] | None = None) -> dict[str, Any]:
    init_store(store)
    state = load_state(store)
    roots = [Path(path) for path in state.get("source_roots", []) if Path(path).exists()]
    items = ingest(roots, max_chars=3600, max_files=max_files, extensions=extensions or DEFAULT_EXTENSIONS) if roots else []
    note_items = [note_to_corpus_item(note) for note in read_notes(store)]
    items.extend(note_items)
    payload = write_dataset(store, items, source_roots=[str(path) for path in roots])
    state["last_build"] = {"at": utc_now(), **payload, "notes": len(note_items)}
    save_state(store, state)
    return {"ok": True, "store": str(store), **payload, "notes": len(note_items)}


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
    proof = result.route_proof
    if proof.get("conflict_pairs") or proof.get("exposure_summary", {}).get("masked_selected", 0):
        return "contradiction_aware"
    if any(row.get("reason") in {"decoy_not_admissible_as_authority", "stale_not_requested"} for row in proof.get("rejected_evidence", [])):
        return "contradiction_aware"
    if len(result.selected_ids) > 1:
        return "proof_lite"
    return "compact_default"


def query_store(store: Path, *, query: str, variant: str = "auto", top_k: int = 5) -> dict[str, Any]:
    data = dataset_path(store)
    if not (data / "corpus" / "corpus_items.jsonl").exists():
        build_store(store)
    items = load_corpus(data)
    router = MoMEMoCERouter(items, candidate_backend="indexed", dataset_path=data, top_k=top_k)
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
        "query": query,
        "variant": chosen_variant,
        "decision": result.decision,
        "answerability": result.frontier_packet.get("answerability"),
        "selected_ids": result.selected_ids,
        "selected_count": len(result.selected_ids),
        "latency_ms": round(latency_ms, 3),
        "packet_words": rough_tokens(packet_text),
        "packet_text": packet_text,
        "route_proof": result.route_proof,
        "packet_path": str(packet_path),
    }


def status(store: Path) -> dict[str, Any]:
    init_store(store)
    state = load_state(store)
    data = dataset_path(store)
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
                self._send(200, query_store(self.store, query=str(payload["query"]), variant=str(payload.get("variant", "auto"))))
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

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8768)
    serve_parser.add_argument("--stdio-mcp-placeholder", action="store_true", help=argparse.SUPPRESS)

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
            print_payload(query_store(store, query=args.query, variant=args.variant, top_k=args.top_k), text=args.text)
        elif args.command == "serve":
            if args.stdio_mcp_placeholder:
                print(json.dumps({"ok": False, "error": "MCP protocol server is not implemented yet; use HTTP serve or CLI commands."}))
                return 2
            serve(store, host=args.host, port=args.port)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
