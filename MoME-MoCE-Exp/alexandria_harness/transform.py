from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .engine_client import EngineSnapshot
from .validate import collect_contract_issues, extract_route_proof


HARNESS_VERSION = "alexandria.harness.v0.1"
VIEW_VERSION = "alexandria.dashboard_view.v0.1"


def build_dashboard_view(
    snapshot: EngineSnapshot | dict[str, Any],
    packet_response: dict[str, Any] | None = None,
    proof_response: dict[str, Any] | None = None,
    *,
    api_base: str = "http://127.0.0.1:8766",
    command: str | None = None,
    action_message: str | None = None,
) -> dict[str, Any]:
    snapshot_dict = snapshot.to_dict() if isinstance(snapshot, EngineSnapshot) else snapshot
    issues = collect_contract_issues(snapshot_dict, packet_response, proof_response) if packet_response else _snapshot_issues(snapshot_dict)
    health = snapshot_dict.get("health", {}) if isinstance(snapshot_dict, dict) else {}
    hooks = snapshot_dict.get("hooks", {}) if isinstance(snapshot_dict, dict) else {}
    memories = snapshot_dict.get("memories", {}) if isinstance(snapshot_dict, dict) else {}
    memory_items = [item for item in memories.get("items", []) if isinstance(item, dict)]
    packet = packet_response.get("packet", {}) if packet_response else {}
    evidence = [item for item in packet.get("evidence", []) if isinstance(item, dict)]
    selected_ids = packet_response.get("selected_ids", []) if packet_response else []
    proof = _safe_proof(proof_response)
    query = command or packet.get("query") or ""
    max_evidence = packet.get("context_budget", {}).get("max_evidence_items", len(evidence))

    view = {
        "view_version": VIEW_VERSION,
        "harness_version": HARNESS_VERSION,
        "generated_at": _utc_now(),
        "api_base": api_base.rstrip("/"),
        "command": query,
        "status": {
            "connection": "online" if health.get("ok") is True else "offline",
            "valid": bool(issues["valid"]),
            "errors": issues["errors"],
            "warnings": issues["warnings"],
            "service_version": health.get("service_version", ""),
            "candidate_backend": health.get("candidate_backend", ""),
            "memory_count": int(health.get("memory_count") or 0),
            "action_message": action_message or "",
        },
        "model_packet": packet if packet_response and issues["valid"] else None,
        "dashboard_proof": proof,
        "dashboard": {
            "metrics": {
                "admissible_packet": _format_size(packet),
                "admissible_packet_bytes": len(json.dumps(packet, ensure_ascii=False)),
                "confidence": _confidence_percent(packet_response.get("confidence") if packet_response else 0),
                "fresh_items": sum(1 for item in memory_items if item.get("staleness") in (None, "", "current")),
                "stale_items": sum(1 for item in memory_items if item.get("staleness") not in (None, "", "current")),
                "trusted_sources": _trusted_source_count(evidence or memory_items),
                "latency_ms": packet_response.get("latency_ms") if packet_response else None,
            },
            "memory_overview": _memory_overview(memory_items),
            "context_packet": {
                "objective": query,
                "answerability": packet.get("answerability", "unknown"),
                "relevant_memory": len(evidence),
                "trusted_sources": _trusted_source_count(evidence),
                "policy_constraints": len(packet.get("constraints", []) or []),
                "bullets": _context_bullets(evidence, has_packet=packet_response is not None),
                "admitted_label": f"{len(evidence)}/{max_evidence}",
                "excluded_label": f"{max(0, int(max_evidence or 0) - len(evidence))} items",
                "why_excluded": "stale, low relevance, blocked policy, or outside current intent",
            },
            "proof_timeline": _proof_timeline(health, packet_response, proof, packet),
            "sources": _sources(evidence, memory_items),
            "source_rows": _source_rows(evidence, memory_items),
            "memory_rows": _memory_rows(memory_items),
            "api_preview": {
                "request": {
                    "query": query,
                    "strategy": packet_response.get("strategy", "helper-lazy") if packet_response else "helper-lazy",
                    "include_proof": False,
                    "max_evidence_items": max_evidence,
                },
                "response": _format_size(packet),
                "time": f"{packet_response.get('latency_ms', 0):.3f} ms" if packet_response else "not run",
                "confidence": f"{_confidence_percent(packet_response.get('confidence') if packet_response else 0)}%",
            },
            "endpoints": hooks.get("endpoints", []),
        },
        "raw_refs": {
            "route_id": packet_response.get("route_id") if packet_response else "",
            "selected_ids": selected_ids,
            "proof_available": proof_response is not None,
        },
    }
    return view


def _snapshot_issues(snapshot: dict[str, Any]) -> dict[str, Any]:
    return collect_contract_issues(snapshot, _minimal_empty_packet(), None)


def _minimal_empty_packet() -> dict[str, Any]:
    return {
        "route_id": "not_run",
        "strategy": "helper-lazy",
        "decision": "not_run",
        "confidence": 0,
        "selected_ids": [],
        "latency_ms": 0,
        "packet": {
            "packet_version": "alexandria.empty_packet.v0.1",
            "role": "frontier_model_context_packet",
            "query": "not run",
            "evidence": [],
            "context_budget": {"max_evidence_items": 0, "selected_evidence_items": 0, "frontier_packet_tokens": 0},
            "constraints": [],
        },
        "artifact_errors": [],
    }


def _safe_proof(proof_response: dict[str, Any] | None) -> dict[str, Any] | None:
    if not proof_response:
        return None
    try:
        return extract_route_proof(proof_response)
    except Exception:
        return None


def _memory_overview(memories: list[dict[str, Any]]) -> dict[str, int]:
    preferences = 0
    policies = 0
    aliases = 0
    projects: set[str] = set()
    for item in memories:
        tags = [str(tag) for tag in item.get("tags", [])]
        aliases += len(item.get("aliases", []) or [])
        if item.get("claim_type") == "preference" or "preference" in tags:
            preferences += 1
        if item.get("claim_type") == "policy" or item.get("safety_label") not in (None, "", "normal"):
            policies += 1
        projects.update(tag for tag in tags if "project" in tag or "repo" in tag)
    return {
        "preferences": preferences,
        "aliases": aliases,
        "projects": len(projects),
        "policies": policies,
        "notes": max(0, len(memories) - preferences - policies),
        "total": len(memories),
    }


def _context_bullets(evidence: list[dict[str, Any]], *, has_packet: bool) -> list[str]:
    if not evidence:
        if has_packet:
            return ["No admitted memory for this command. The model should answer without project memory."]
        return []
    return [f"{_source_name(item)}: {_truncate(str(item.get('text') or item.get('id') or ''), 130)}" for item in evidence[:6]]


def _proof_timeline(
    health: dict[str, Any],
    packet_response: dict[str, Any] | None,
    proof: dict[str, Any] | None,
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    if not packet_response:
        return [{"stage": "Idle", "label": "No packet requested", "detail": "Harness has only loaded service state"}]
    selected = len(packet_response.get("selected_ids", []) or [])
    route_count = len(proof.get("routes", []) or []) if proof else 0
    rejected = len(proof.get("intent_guard_rejections", []) or []) if proof else 0
    return [
        {"stage": "Ingest", "label": f"{health.get('memory_count', 0)} memories loaded", "detail": health.get("candidate_backend", "")},
        {"stage": "Route", "label": f"{packet_response.get('strategy')} via {route_count or 1} route(s)", "detail": packet_response.get("decision", "")},
        {"stage": "Evaluate", "label": f"{selected} admitted; {rejected} guard reject(s)", "detail": "admission gates applied"},
        {"stage": "Assemble", "label": f"packet built ({_format_size(packet)})", "detail": f"{packet.get('context_budget', {}).get('frontier_packet_tokens', 0)} est. tokens"},
        {"stage": "Output", "label": "proof stored", "detail": packet_response.get("route_id", "")},
    ]


def _sources(evidence: list[dict[str, Any]], memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = evidence or memories[:5]
    return [
        {
            "name": _source_name(item),
            "type": _title(str(item.get("source_family") or "memory")),
            "status": _status_label(item),
            "time": item.get("created_at") or "stored",
        }
        for item in items[:5]
    ]


def _source_rows(evidence: list[dict[str, Any]], memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = evidence or memories[:8]
    return [
        {
            "name": _source_name(item),
            "type": _title(str(item.get("source_family") or "memory")),
            "status": _status_label(item),
            "last_seen": item.get("created_at") or "stored",
            "route_note": "admitted candidate" if item.get("staleness") in (None, "", "current") else f"{item.get('staleness')} evidence",
        }
        for item in items[:8]
    ]


def _memory_rows(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "fact": _truncate(str(item.get("text_preview") or item.get("text") or item.get("id") or ""), 96),
            "type": _title(str(item.get("claim_type") or item.get("source_family") or "fact")),
            "cluster": (item.get("tags") or [item.get("source_family") or "memory"])[0],
            "freshness": "fresh" if item.get("staleness") in (None, "", "current") else "stale",
            "last_seen": item.get("created_at") or "stored",
        }
        for item in memories[:8]
    ]


def _trusted_source_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("authority") in (None, "", "high", "medium"))


def _source_name(item: dict[str, Any]) -> str:
    provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
    artifact_path = str(provenance.get("artifact_path") or "")
    if artifact_path:
        return artifact_path.replace("\\", "/").rstrip("/").split("/")[-1]
    return str(item.get("id") or item.get("source_family") or "memory")


def _status_label(item: dict[str, Any]) -> str:
    if item.get("staleness") not in (None, "", "current"):
        return _title(str(item.get("staleness")))
    if item.get("safety_label") not in (None, "", "normal"):
        return _title(str(item.get("safety_label")))
    if item.get("authority") in (None, "", "high", "medium"):
        return "Verified"
    return _title(str(item.get("authority")))


def _confidence_percent(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if number <= 1:
        number *= 100
    return max(0, min(100, round(number)))


def _format_size(value: Any) -> str:
    size = len(json.dumps(value or {}, ensure_ascii=False))
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def _title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
