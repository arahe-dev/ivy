from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from mome_moce_harness import (
        MoMEMoCERouter,
        RouteResult,
        load_corpus,
        validate_route_artifacts,
    )
    from run_librarian_advisor_harness import (
        helper_lazy_advice,
        route_librarian_bundle,
    )
except ModuleNotFoundError:
    from scripts.mome_moce_harness import (
        MoMEMoCERouter,
        RouteResult,
        load_corpus,
        validate_route_artifacts,
    )
    from scripts.run_librarian_advisor_harness import (
        helper_lazy_advice,
        route_librarian_bundle,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "out" / "d_acca_dogfood"
SERVICE_VERSION = "d_acca.dogfood_hooks.v0.1"
VALID_SOURCE_FAMILIES = {
    "doc_memory",
    "runbook",
    "benchmark_artifact",
    "safety_policy",
    "workflow_trace",
    "debug_failure",
    "source_code",
    "distractor",
}
VALID_AUTHORITIES = {"high", "medium", "low", "decoy"}
VALID_STALENESS = {"current", "stale", "unknown", "decoy"}
VALID_SAFETY = {"normal", "safety_critical", "unsafe_decoy", "secret_like"}
VALID_STRATEGIES = {"d-acca", "helper-lazy"}


class DogfoodError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_slug(value: str, *, fallback: str = "memory") -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_-")
    if not value or not re.match(r"^[a-z0-9]", value):
        value = fallback
    return value[:96]


def unique_strs(values: Any, *, lowercase: bool = False, limit: int | None = None) -> list[str]:
    if values is None:
        raw_values: list[Any] = []
    elif isinstance(values, list):
        raw_values = values
    elif isinstance(values, str):
        raw_values = [values]
    else:
        raw_values = [str(values)]
    out: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        text = str(value).strip()
        if not text:
            continue
        if lowercase:
            text = text.lower()
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if limit is not None and len(out) >= limit:
            break
    return out


def coerce_pattern_list(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    patterns: list[list[str]] = []
    for pattern in value:
        terms = unique_strs(pattern, limit=8)
        if terms:
            patterns.append(terms)
    return patterns[:24]


def safe_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


class DogfoodHooks:
    def __init__(
        self,
        root: Path = DEFAULT_ROOT,
        *,
        candidate_backend: str = "indexed",
        top_k: int = 5,
    ) -> None:
        self.root = root.resolve()
        self.dataset = self.root / "dataset"
        self.corpus_path = self.dataset / "corpus" / "corpus_items.jsonl"
        self.routes_dir = self.root / "routes"
        self.feedback_path = self.root / "feedback.jsonl"
        self.forget_path = self.root / "forget_events.jsonl"
        self.import_path = self.root / "imports.jsonl"
        self.candidate_backend = candidate_backend
        self.top_k = top_k
        self._router: MoMEMoCERouter | None = None
        self._router_mtime_ns: int | None = None
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        (self.dataset / "corpus").mkdir(parents=True, exist_ok=True)
        (self.dataset / "eval").mkdir(parents=True, exist_ok=True)
        (self.dataset / "metadata").mkdir(parents=True, exist_ok=True)
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        if not self.corpus_path.exists():
            self.corpus_path.write_text("", encoding="utf-8")

    def _read_records(self) -> list[dict[str, Any]]:
        self._ensure_layout()
        records: list[dict[str, Any]] = []
        with self.corpus_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                records.append(json.loads(line))
        return records

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        self._ensure_layout()
        tmp_path = self.corpus_path.with_suffix(".jsonl.tmp")
        lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
        tmp_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        tmp_path.replace(self.corpus_path)
        self._router = None
        self._router_mtime_ns = None

    def _router_for_current_corpus(self) -> MoMEMoCERouter:
        self._ensure_layout()
        mtime_ns = self.corpus_path.stat().st_mtime_ns
        if self._router is None or self._router_mtime_ns != mtime_ns:
            self._router = MoMEMoCERouter(
                load_corpus(self.dataset),
                top_k=self.top_k,
                candidate_backend=self.candidate_backend,
                dataset_path=self.dataset,
            )
            self._router_mtime_ns = mtime_ns
        return self._router

    def hooks(self) -> dict[str, Any]:
        return {
            "service_version": SERVICE_VERSION,
            "description": "Local D-ACCA dogfood hooks. Use these from a dashboard, MCP wrapper, or ChatGPT App backend.",
            "model_visible_default": "Only /packet.packet is intended for model-visible use. Use /proof for debug-only route details.",
            "endpoints": [
                {"method": "GET", "path": "/health", "read_only": True},
                {"method": "GET", "path": "/hooks", "read_only": True},
                {"method": "GET", "path": "/memories?limit=50&offset=0", "read_only": True},
                {"method": "GET", "path": "/search?q=...&limit=10&include_text=false", "read_only": True},
                {"method": "GET", "path": "/proof/{route_id}", "read_only": True},
                {"method": "POST", "path": "/ingest", "read_only": False},
                {"method": "POST", "path": "/packet", "read_only": True},
                {"method": "POST", "path": "/feedback", "read_only": False},
                {"method": "POST", "path": "/forget", "read_only": False},
            ],
            "packet_strategies": sorted(VALID_STRATEGIES),
            "request_examples": {
                "ingest": {
                    "items": [
                        {
                            "text": "Signal pings are delivered through the local daemon and phone bridge.",
                            "source_family": "runbook",
                            "authority": "high",
                            "tags": ["signal", "phone"],
                            "aliases": ["ping my phone", "signalcli"],
                        }
                    ]
                },
                "packet": {"query": "how do I ping my phone from the agent?", "strategy": "helper-lazy"},
                "feedback": {"route_id": "route_...", "rating": "useful", "note": "correct packet"},
                "forget": {"ids": ["manual_signal_bridge_abcd1234"], "reason": "user requested deletion"},
            },
        }

    def health(self) -> dict[str, Any]:
        records = self._read_records()
        return {
            "ok": True,
            "service_version": SERVICE_VERSION,
            "root": str(self.root),
            "candidate_backend": self.candidate_backend,
            "memory_count": len(records),
            "time": utc_now(),
        }

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        incoming = self._extract_incoming_items(payload)
        if not incoming:
            raise DogfoodError("ingest requires text, documents, or items")

        existing = {record["id"]: record for record in self._read_records()}
        imported_ids: list[str] = []
        import_id = "import_" + sha256_text(canonical_json({"payload": payload, "time": utc_now()}))[:12]
        for index, item in enumerate(incoming):
            record = self._normalize_ingest_item(item, import_id=import_id, index=index)
            existing[record["id"]] = record
            imported_ids.append(record["id"])

        records = sorted(existing.values(), key=lambda record: record["id"])
        self._write_records(records)
        self._append_jsonl(
            self.import_path,
            {
                "import_id": import_id,
                "created_at": utc_now(),
                "ids": imported_ids,
                "count": len(imported_ids),
                "source": payload.get("source") or payload.get("project") or "manual",
            },
        )
        return {"import_id": import_id, "ingested": len(imported_ids), "ids": imported_ids, "memory_count": len(records)}

    def _extract_incoming_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if isinstance(payload.get("items"), list):
            items.extend(dict(item) for item in payload["items"] if isinstance(item, dict))
        if isinstance(payload.get("documents"), list):
            for doc in payload["documents"]:
                if isinstance(doc, dict):
                    items.append(dict(doc))
        if isinstance(payload.get("text"), str) and payload["text"].strip():
            items.append(
                {
                    "id": payload.get("id"),
                    "text": payload["text"],
                    "source": payload.get("source"),
                    "source_family": payload.get("source_family"),
                    "authority": payload.get("authority"),
                    "staleness": payload.get("staleness"),
                    "tags": payload.get("tags"),
                    "aliases": payload.get("aliases"),
                    "project": payload.get("project"),
                }
            )
        defaults = {
            "source": payload.get("source"),
            "project": payload.get("project"),
            "source_family": payload.get("source_family"),
            "authority": payload.get("authority"),
            "staleness": payload.get("staleness"),
            "tags": payload.get("tags"),
        }
        for item in items:
            for key, value in defaults.items():
                if key not in item or item[key] in (None, "", []):
                    item[key] = value
        return items

    def _normalize_ingest_item(self, item: dict[str, Any], *, import_id: str, index: int) -> dict[str, Any]:
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            raise DogfoodError("each ingest item needs non-empty text")

        source_family = str(item.get("source_family") or "doc_memory")
        if source_family not in VALID_SOURCE_FAMILIES:
            source_family = "doc_memory"
        authority = str(item.get("authority") or "medium")
        if authority not in VALID_AUTHORITIES:
            authority = "medium"
        staleness = str(item.get("staleness") or "current")
        if staleness not in VALID_STALENESS:
            staleness = "current"
        safety_label = str(item.get("safety_label") or "normal")
        if safety_label not in VALID_SAFETY:
            safety_label = "normal"

        source = str(item.get("source") or item.get("path") or item.get("project") or "manual")
        provided_id = str(item.get("id") or "").strip()
        digest = sha256_text(text + canonical_json(item))[:12]
        base_id = stable_slug(provided_id or f"{source}_{digest}")
        item_id = f"{base_id}_{digest}" if provided_id and not provided_id.endswith(digest) else base_id

        tags = unique_strs([*unique_strs(item.get("tags"), lowercase=True), source_family, *unique_strs(item.get("project"), lowercase=True)], lowercase=True, limit=16)
        if not tags:
            tags = [source_family]
        aliases = unique_strs(item.get("aliases"), limit=24)
        if not aliases:
            aliases = tags[:6]

        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        provenance = {
            **provenance,
            "artifact_path": str(provenance.get("artifact_path") or f"out/d_acca_dogfood/imports/{import_id}.jsonl"),
            "record_index": int(provenance.get("record_index") or index),
            "generator": str(provenance.get("generator") or "d_acca_dogfood_service"),
            "source_hash": str(provenance.get("source_hash") or digest),
        }

        record: dict[str, Any] = {
            "id": stable_slug(item_id),
            "source_family": source_family,
            "authority": authority,
            "created_at": str(item.get("created_at") or today()),
            "supersedes": unique_strs(item.get("supersedes"), lowercase=True),
            "tags": tags,
            "text": text,
            "provenance": provenance,
            "staleness": staleness,
            "conflicts_with": unique_strs(item.get("conflicts_with"), lowercase=True),
            "safety_label": safety_label,
            "taint_labels": unique_strs(item.get("taint_labels"), lowercase=True),
            "exposure_policy": str(item.get("exposure_policy") or ""),
            "claim_type": str(item.get("claim_type") or "fact"),
            "canonical_for": unique_strs(item.get("canonical_for"), limit=12),
            "aliases": aliases,
            "helper_query": str(item.get("helper_query") or text[:220]).strip(),
            "guard_terms": unique_strs(item.get("guard_terms") or tags[:2], lowercase=True, limit=8),
            "negative_constraints": unique_strs(
                item.get("negative_constraints") or ["Reject stale, decoy, private, or unsupported evidence."],
                limit=8,
            ),
            "replay_match_terms": unique_strs(item.get("replay_match_terms") or aliases, limit=24),
            "distillation_patterns": coerce_pattern_list(item.get("distillation_patterns")),
        }
        record = {key: value for key, value in record.items() if value not in ("", [], None)}
        return record

    def list_memories(self, *, limit: int = 50, offset: int = 0, include_text: bool = False) -> dict[str, Any]:
        records = self._read_records()
        rows = records[offset : offset + limit]
        return {
            "total": len(records),
            "limit": limit,
            "offset": offset,
            "items": [self._memory_view(record, include_text=include_text) for record in rows],
        }

    def search(self, query: str, *, limit: int = 10, include_text: bool = False) -> dict[str, Any]:
        router = self._router_for_current_corpus()
        q_tokens = set(re.findall(r"[a-z0-9_./:-]+", query.lower()))
        rows: list[dict[str, Any]] = []
        for item in router.items:
            raw = item.raw
            aliases = " ".join(str(alias) for alias in raw.get("aliases", []))
            blob = " ".join([item.id, " ".join(item.tags), item.source_family, aliases, item.text]).lower()
            score = sum(1 for token in q_tokens if token and token in blob)
            if query.lower() in blob:
                score += 5
            if score <= 0:
                continue
            row = self._memory_view(raw, include_text=include_text)
            row["score"] = score
            rows.append(row)
        rows.sort(key=lambda row: (-row["score"], row["id"]))
        return {"query": query, "count": len(rows[:limit]), "items": rows[:limit]}

    def packet(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query") or "").strip()
        if not query:
            raise DogfoodError("packet requires query")
        strategy = str(payload.get("strategy") or "helper-lazy")
        if strategy not in VALID_STRATEGIES:
            raise DogfoodError(f"strategy must be one of: {', '.join(sorted(VALID_STRATEGIES))}")
        include_proof = bool(payload.get("include_proof", False))
        max_union_items = safe_int(payload.get("max_evidence_items"), 2, minimum=0, maximum=8)
        route_id = self._route_id(query, strategy)
        router = self._router_for_current_corpus()

        if strategy == "d-acca":
            result = router.route(query)
            response = self._response_from_route_result(
                route_id,
                strategy,
                result,
                item_ids=set(router.items_by_id),
                include_proof=include_proof,
            )
        else:
            response = self._helper_lazy_packet(route_id, query, router, max_union_items=max_union_items, include_proof=include_proof)

        self._write_route_record(route_id, response)
        return response

    def _response_from_route_result(
        self,
        route_id: str,
        strategy: str,
        result: RouteResult,
        *,
        item_ids: set[str],
        include_proof: bool,
    ) -> dict[str, Any]:
        result.route_proof["case_id"] = route_id
        result.frontier_packet["case_id"] = route_id
        errors = validate_route_artifacts(result, item_ids, case_id=route_id)
        response = {
            "service_version": SERVICE_VERSION,
            "route_id": route_id,
            "strategy": strategy,
            "decision": result.decision,
            "confidence": round(result.confidence, 4),
            "selected_ids": result.selected_ids,
            "latency_ms": round(result.latency_ms, 3),
            "packet": result.frontier_packet,
            "route_summary": self._route_summary(result.route_proof),
            "artifact_errors": errors,
        }
        if include_proof:
            response["route_proof"] = result.route_proof
        return response

    def _helper_lazy_packet(
        self,
        route_id: str,
        query: str,
        router: MoMEMoCERouter,
        *,
        max_union_items: int,
        include_proof: bool,
    ) -> dict[str, Any]:
        advice = helper_lazy_advice({"id": route_id, "query": query}, router)
        bundle = route_librarian_bundle(
            router,
            advice,
            case_id=route_id,
            artifact_dir=None,
            max_union_items=max_union_items,
        )
        selected_items = []
        for item_id in bundle["selected_ids"]:
            item = router.items_by_id.get(item_id)
            if item is not None:
                selected_items.append(router._packet_item(item))
        packet = {
            "packet_version": "d_acca.dogfood_context_packet.v0.1",
            "role": "frontier_model_context_packet",
            "query": query,
            "route_id": route_id,
            "strategy": "helper-lazy",
            "answerability": "answerable_with_context" if selected_items else "no_context_needed",
            "instruction": "Use only admitted evidence below. If evidence is empty, answer without project memory.",
            "evidence": selected_items,
            "context_budget": {
                "max_evidence_items": max_union_items,
                "selected_evidence_items": len(selected_items),
                "frontier_packet_tokens": sum(max(1, len(str(item.get("text", "")).split())) for item in selected_items),
            },
            "constraints": [
                "Do not use stale, decoy, private, or rejected evidence.",
                "Cite admitted evidence ids when using memory.",
            ],
        }
        proof = {
            "proof_version": "d_acca.dogfood_route_proof.v0.1",
            "route_id": route_id,
            "strategy": "helper-lazy",
            "query": query,
            "decision": bundle["decision"],
            "selected_ids": bundle["selected_ids"],
            "advice": {
                "strategy": advice.strategy,
                "queries": advice.queries,
                "entity_terms": advice.entity_terms,
                "negative_constraints": advice.negative_constraints,
                "side_tracks": advice.side_tracks,
                "latency_ms": advice.latency_ms,
            },
            "routes": bundle["routes"],
            "intent_guard_rejections": bundle["intent_guard_rejections"],
            "latency_ms": bundle["latency_ms"],
            "created_at": utc_now(),
        }
        response = {
            "service_version": SERVICE_VERSION,
            "route_id": route_id,
            "strategy": "helper-lazy",
            "decision": bundle["decision"],
            "confidence": 0.9 if selected_items else 0.55,
            "selected_ids": bundle["selected_ids"],
            "latency_ms": bundle["latency_ms"],
            "packet": packet,
            "route_summary": self._route_summary(proof),
            "artifact_errors": bundle["artifact_errors"],
        }
        if include_proof:
            response["route_proof"] = proof
        else:
            response["_proof_path"] = f"/proof/{route_id}"
        response["_stored_route_proof"] = proof
        return response

    def proof(self, route_id: str) -> dict[str, Any]:
        route_id = stable_slug(route_id, fallback="route")
        path = self.routes_dir / f"{route_id}.json"
        if not path.exists():
            raise DogfoodError(f"unknown route_id: {route_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        route_id = str(payload.get("route_id") or "").strip()
        rating = str(payload.get("rating") or "").strip().lower()
        if not route_id:
            raise DogfoodError("feedback requires route_id")
        if rating not in {"useful", "wrong", "missed", "stale", "private", "neutral"}:
            raise DogfoodError("rating must be useful, wrong, missed, stale, private, or neutral")
        record = {
            "created_at": utc_now(),
            "route_id": stable_slug(route_id, fallback="route"),
            "rating": rating,
            "note": str(payload.get("note") or payload.get("notes") or "").strip(),
            "expected_ids": unique_strs(payload.get("expected_ids"), lowercase=True),
            "tags": unique_strs(payload.get("tags"), lowercase=True),
        }
        self._append_jsonl(self.feedback_path, record)
        return {"saved": True, "feedback": record}

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        ids = unique_strs(payload.get("ids") or payload.get("id"), lowercase=True)
        if not ids:
            raise DogfoodError("forget requires ids")
        records = self._read_records()
        kept = [record for record in records if record["id"] not in set(ids)]
        removed = len(records) - len(kept)
        self._write_records(kept)
        event = {
            "created_at": utc_now(),
            "ids": ids,
            "removed": removed,
            "reason": str(payload.get("reason") or "").strip(),
        }
        self._append_jsonl(self.forget_path, event)
        return {"removed": removed, "ids": ids, "memory_count": len(kept)}

    def _memory_view(self, record: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
        view = {
            "id": record["id"],
            "source_family": record.get("source_family"),
            "authority": record.get("authority"),
            "created_at": record.get("created_at"),
            "claim_type": record.get("claim_type"),
            "staleness": record.get("staleness"),
            "safety_label": record.get("safety_label"),
            "exposure_policy": record.get("exposure_policy"),
            "tags": record.get("tags", []),
            "aliases": record.get("aliases", []),
            "provenance": record.get("provenance", {}),
        }
        if include_text:
            view["text"] = record.get("text", "")
        else:
            text = str(record.get("text", ""))
            view["text_preview"] = text[:180] + ("..." if len(text) > 180 else "")
        return view

    def _route_id(self, query: str, strategy: str) -> str:
        millis = int(time.time() * 1000)
        digest = sha256_text(f"{millis}:{strategy}:{query}")[:10]
        return f"route_{millis}_{digest}"

    def _route_summary(self, proof: dict[str, Any]) -> dict[str, Any]:
        return {
            "route_id": proof.get("route_id") or proof.get("case_id"),
            "proof_version": proof.get("proof_version"),
            "decision": proof.get("decision"),
            "selected_ids": proof.get("selected_ids") or proof.get("selected_evidence") or [],
            "latency_ms": proof.get("latency_ms"),
        }

    def _write_route_record(self, route_id: str, response: dict[str, Any]) -> None:
        stored = dict(response)
        if "_stored_route_proof" in stored:
            stored["route_proof"] = stored.pop("_stored_route_proof")
        stored.pop("_proof_path", None)
        path = self.routes_dir / f"{stable_slug(route_id, fallback='route')}.json"
        path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
        response.pop("_stored_route_proof", None)

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    data = handler.rfile.read(length)
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise DogfoodError("JSON body must be an object")
    return payload


def write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Max-Age", "600")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def make_handler(hooks: DogfoodHooks) -> type[BaseHTTPRequestHandler]:
    class DogfoodHttpHandler(BaseHTTPRequestHandler):
        server_version = "DAccaDogfoodHooks/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                path = parsed.path.rstrip("/") or "/"
                if path == "/health":
                    write_json(self, 200, hooks.health())
                elif path == "/hooks":
                    write_json(self, 200, hooks.hooks())
                elif path == "/memories":
                    write_json(
                        self,
                        200,
                        hooks.list_memories(
                            limit=safe_int(first_query_value(query, "limit"), 50, minimum=1, maximum=500),
                            offset=safe_int(first_query_value(query, "offset"), 0, minimum=0, maximum=1_000_000),
                            include_text=parse_bool(first_query_value(query, "include_text")),
                        ),
                    )
                elif path == "/search":
                    q = first_query_value(query, "q") or first_query_value(query, "query") or ""
                    write_json(
                        self,
                        200,
                        hooks.search(
                            q,
                            limit=safe_int(first_query_value(query, "limit"), 10, minimum=1, maximum=100),
                            include_text=parse_bool(first_query_value(query, "include_text")),
                        ),
                    )
                elif path.startswith("/proof/"):
                    write_json(self, 200, hooks.proof(path.split("/", 2)[2]))
                else:
                    write_json(self, 404, {"error": "not_found", "path": parsed.path})
            except Exception as exc:  # pragma: no cover - exercised by manual dogfood.
                write_json(self, 400, {"error": type(exc).__name__, "message": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
                payload = read_json_body(self)
                if path == "/ingest":
                    write_json(self, 200, hooks.ingest(payload))
                elif path == "/packet":
                    write_json(self, 200, hooks.packet(payload))
                elif path == "/feedback":
                    write_json(self, 200, hooks.feedback(payload))
                elif path == "/forget":
                    write_json(self, 200, hooks.forget(payload))
                else:
                    write_json(self, 404, {"error": "not_found", "path": path})
            except Exception as exc:  # pragma: no cover - exercised by manual dogfood.
                write_json(self, 400, {"error": type(exc).__name__, "message": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DogfoodHttpHandler


def first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None


def parse_bool(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def serve(args: argparse.Namespace) -> int:
    hooks = DogfoodHooks(Path(args.root), candidate_backend=args.candidate_backend, top_k=args.top_k)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(hooks))
    print(f"D-ACCA dogfood hooks listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D-ACCA dogfood hooks service")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="start HTTP JSON hook service")
    serve_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8766)
    serve_parser.add_argument("--candidate-backend", choices=["scan", "indexed", "rust"], default="indexed")
    serve_parser.add_argument("--top-k", type=int, default=5)
    serve_parser.set_defaults(func=serve)

    hooks_parser = subparsers.add_parser("hooks", help="print hook discovery JSON")
    hooks_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    hooks_parser.set_defaults(func=lambda args: print_json(DogfoodHooks(Path(args.root)).hooks()))

    ingest_parser = subparsers.add_parser("ingest", help="ingest one text memory")
    ingest_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    ingest_parser.add_argument("--text", required=True)
    ingest_parser.add_argument("--source", default="manual")
    ingest_parser.add_argument("--tag", action="append", default=[])
    ingest_parser.set_defaults(
        func=lambda args: print_json(
            DogfoodHooks(Path(args.root)).ingest({"text": args.text, "source": args.source, "tags": args.tag})
        )
    )

    packet_parser = subparsers.add_parser("packet", help="build an admissible context packet")
    packet_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    packet_parser.add_argument("--query", required=True)
    packet_parser.add_argument("--strategy", choices=sorted(VALID_STRATEGIES), default="helper-lazy")
    packet_parser.add_argument("--include-proof", action="store_true")
    packet_parser.set_defaults(
        func=lambda args: print_json(
            DogfoodHooks(Path(args.root)).packet(
                {"query": args.query, "strategy": args.strategy, "include_proof": args.include_proof}
            )
        )
    )

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    result = args.func(args)
    return 0 if result is None else int(result)


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
