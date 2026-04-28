from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .memory_packet import MemoryCandidate, RoutingDecision
from .memory_search import hybrid_search, keyword_search, vector_search
from .memory_store import DEFAULT_DB_PATH, MemoryStore


POLICY_DIR = Path(__file__).resolve().parent / "memory_policies"


TASK_RULES = [
    ("tool_debug", ["json", "tool call", "validation", "invalid", "think", "reasoning tags"]),
    ("safety", ["absolute path", "policy", "sandbox", "unsafe", "rejected"]),
    ("benchmark", ["qwen", "benchmark", "tps", "ctx", "decode_tps", "gpu", "4060"]),
    ("workflow", ["workflow", "successful", "calc write", "procedure", "steps"]),
    ("planning", ["plan", "architecture", "phase", "roadmap"]),
]


DEFAULT_POLICIES = {
    "general": "hybrid_default",
    "tool_debug": "failure_first",
    "benchmark": "benchmark",
    "safety": "safety_first",
    "workflow": "hybrid_default",
    "planning": "hybrid_default",
}


def classify_task(query: str) -> str:
    q = query.lower()
    for task_type, terms in TASK_RULES:
        if any(term in q for term in terms):
            return task_type
    return "general"


def load_policy(name: str | None, task_type: str = "general") -> dict[str, Any]:
    policy_name = name or DEFAULT_POLICIES.get(task_type, "hybrid_default")
    path = POLICY_DIR / f"{policy_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Memory policy not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def select_composers(task_type: str) -> list[str]:
    if task_type == "tool_debug":
        return ["debugging", "safety"]
    if task_type == "benchmark":
        return ["benchmark"]
    if task_type == "safety":
        return ["safety"]
    if task_type == "workflow":
        return ["workflow", "safety"]
    if task_type == "planning":
        return ["planning", "minimal"]
    return ["minimal"]


def provenance_present(row: dict[str, Any]) -> bool:
    return bool(row.get("source_artifact_path") or row.get("source_episode_id") or row.get("run_id") or row.get("artifact_path"))


def candidate_from_result(row: dict[str, Any], expert: str, boost: float = 0.0) -> MemoryCandidate:
    score = row.get("score")
    try:
        numeric = float(score) if score is not None else 0.0
    except Exception:
        numeric = 0.0
    if numeric < 0:
        numeric = 1.0 / (1.0 + abs(numeric))
    return MemoryCandidate(
        memory_item_id=row.get("memory_item_id") or row.get("id"),
        text=str(row.get("text") or ""),
        kind=row.get("kind"),
        score=numeric + boost,
        source_expert=expert,
        source_episode_id=row.get("source_episode_id"),
        source_artifact_path=row.get("source_artifact_path") or row.get("artifact_path"),
        run_id=row.get("run_id"),
        provenance_present=provenance_present(row),
        metadata={k: v for k, v in row.items() if k not in {"text"}},
    )


def _direct_query(db_path: Path, where: str, params: tuple[Any, ...], expert: str, limit: int) -> list[MemoryCandidate]:
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    try:
        rows = conn.execute(
            f"""
            SELECT mi.id AS memory_item_id, mi.text, mi.kind, mi.importance, mi.confidence,
                   mi.source_episode_id, mi.source_artifact_path, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE {where}
            ORDER BY mi.created_at DESC, mi.id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["score"] = float(d.get("importance") or 0.5)
            out.append(candidate_from_result(d, expert))
        return out
    finally:
        conn.close()


def run_expert(expert: str, query: str, db_path: Path, limit: int) -> list[MemoryCandidate]:
    if expert == "keyword":
        rows, _ = keyword_search(query, db_path, limit)
        return [candidate_from_result(r, expert, 0.1) for r in rows]
    if expert == "vector":
        return [candidate_from_result(r, expert) for r in vector_search(query, db_path, limit)]
    if expert == "hybrid":
        return [candidate_from_result(r, expert, 0.15) for r in hybrid_search(query, db_path, limit)]
    if expert == "recent":
        return _direct_query(db_path, "1=1", (), expert, limit)
    if expert == "failure":
        like = "%failed%|%failure%|%invalid%|%rejected%|%policy%|%error%|%think%|%json%"
        terms = [t for t in like.split("|")]
        where = " OR ".join(["LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE ?" for _ in terms])
        return _direct_query(db_path, where, tuple(terms), expert, limit)
    if expert == "benchmark":
        terms = ("%qwen%", "%benchmark%", "%decode_tps%", "%ctx=%")
        where = " OR ".join(["LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE ?" for _ in terms])
        return _direct_query(db_path, where, terms, expert, limit)
    if expert == "safety":
        terms = ("%policy%", "%sandbox%", "%path%", "%write%", "%delete%", "%network%", "%unsafe%")
        where = " OR ".join(["LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE ?" for _ in terms])
        return _direct_query(db_path, where, terms, expert, limit)
    if expert in {"procedure", "workflow"}:
        terms = ("%successful%", "%workflow%", "%tool%", "%calc%", "%write%", "%procedure%")
        where = " OR ".join(["LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE ?" for _ in terms])
        return _direct_query(db_path, where, terms, expert, limit)
    if expert == "none":
        return []
    return []


def exact_term_bonus(query: str, candidate: MemoryCandidate) -> float:
    q_terms = set(re.findall(r"[a-z0-9_=.]+", query.lower()))
    blob = f"{candidate.text} {candidate.kind or ''} {candidate.source_artifact_path or ''}".lower()
    if not q_terms:
        return 0.0
    hits = sum(1 for term in q_terms if term in blob)
    return hits / max(1, len(q_terms))


def task_type_bonus(task_type: str, candidate: MemoryCandidate) -> float:
    blob = f"{candidate.text} {candidate.kind or ''}".lower()
    if task_type == "benchmark" and any(t in blob for t in ("qwen", "benchmark", "decode_tps", "ctx=")):
        return 1.0
    if task_type == "tool_debug" and any(t in blob for t in ("json", "validation", "think", "invalid", "failure")):
        return 1.0
    if task_type == "safety" and any(t in blob for t in ("policy", "sandbox", "path", "unsafe")):
        return 1.0
    if task_type == "workflow" and any(t in blob for t in ("successful", "workflow", "calc", "write")):
        return 1.0
    return 0.0


def route_memory(
    query: str,
    db_path: str | Path | None = None,
    policy_name: str | None = None,
    top_k: int | None = None,
    max_packet_chars: int | None = None,
    require_provenance: bool | None = None,
) -> tuple[RoutingDecision, list[MemoryCandidate]]:
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    task_type = classify_task(query)
    policy = load_policy(policy_name, task_type)
    selected_experts = list(policy.get("enabled_experts") or [])
    effective_top_k = int(top_k or policy.get("default_top_k") or 5)
    per_expert = int(policy.get("max_candidates_per_expert") or effective_top_k)
    max_chars = int(max_packet_chars or policy.get("max_packet_chars") or 1800)
    require_prov = bool(policy.get("require_provenance", False) if require_provenance is None else require_provenance)
    weights = policy.get("scoring_weights") or {}

    collected: list[MemoryCandidate] = []
    for expert in selected_experts:
        collected.extend(run_expert(expert, query, db, per_expert))

    deduped: dict[str, MemoryCandidate] = {}
    for candidate in collected:
        key = str(candidate.memory_item_id) if candidate.memory_item_id is not None else f"{candidate.source_expert}:{candidate.text}"
        if require_prov and not candidate.provenance_present:
            continue
        score = candidate.score * float(weights.get("base_score", 1.0))
        if candidate.provenance_present:
            score += float(weights.get("provenance_bonus", 0.25))
        else:
            score -= float(weights.get("missing_provenance_penalty", 0.4))
        score += exact_term_bonus(query, candidate) * float(weights.get("exact_term_bonus", 0.2))
        score += task_type_bonus(task_type, candidate) * float(weights.get("task_type_bonus", 0.2))
        candidate.score = round(score, 6)
        if key not in deduped or candidate.score > deduped[key].score:
            deduped[key] = candidate

    ranked = sorted(deduped.values(), key=lambda c: (c.score, c.provenance_present), reverse=True)
    decision = RoutingDecision(
        query=query,
        task_type=task_type,
        selected_policy=policy["name"],
        selected_experts=selected_experts,
        selected_composers=select_composers(task_type),
        top_k=effective_top_k,
        max_packet_chars=max_chars,
    )
    return decision, ranked[:effective_top_k]
