from __future__ import annotations

import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .memory_packet import MemoryCandidate, RoutingDecision
from .memory_router import (
    candidate_from_result,
    classify_source_family,
    classify_task,
    concept_matches,
    exact_memory_eval_runbook_candidates,
    exact_term_bonus,
    is_memory_eval_command_query,
    run_expert,
    select_composers,
    task_type_bonus,
    wrong_command_family_penalty,
)
from .memory_store import DEFAULT_DB_PATH, MemoryStore
from .mome_policy import MomePolicy, load_mome_policy


EXPERT_ALIASES = {
    "exact_keyword": "keyword",
    "keyword": "keyword",
    "vector_fuzzy": "vector",
    "vector": "vector",
    "hybrid": "hybrid",
    "recent_buffer": "recent",
    "recent": "recent",
    "failure_debug": "failure",
    "failure": "failure",
    "benchmark": "benchmark",
    "safety_policy": "safety",
    "safety": "safety",
    "workflow_procedure": "workflow",
    "workflow": "workflow",
    "runbook_docs": "runbook_docs",
    "runbook": "runbook_docs",
    "none": "none",
}


@dataclass
class MomeRouteResult:
    decision: RoutingDecision
    candidates: list[MemoryCandidate]
    policy: dict[str, Any]
    metadata: dict[str, Any]


def classify_mome_task(query: str) -> str:
    q = query.lower().replace("-", "_")
    if is_memory_eval_command_query(query) or (
        ("command" in q or "runbook" in q or "artifacts" in q or "where" in q)
        and any(term in q for term in ("memory", "eval", "rerun", "docs"))
    ):
        return "runbook"
    if any(term in q for term in ("json", "tool call", "validation", "invalid", "think", "reasoning tags")):
        return "tool_debug"
    if any(term in q for term in ("qwen", "benchmark", "decode_tps", "ctx", "4060", "gpu", "tps")):
        return "benchmark"
    if any(term in q for term in ("absolute path", "sandbox", "policy", "unsafe", "rejected", "delete", "network")):
        return "safety"
    if any(term in q for term in ("workflow", "successful", "calc write", "procedure", "fs_read", "fs_write", "json_validate")):
        return "workflow"
    if ("calculate" in q or "calc" in q) and ("write" in q or "out/" in q):
        return "workflow"
    base = classify_task(query)
    return "general" if base == "planning" else base


def select_mome_composers(task_type: str) -> list[str]:
    if task_type == "runbook":
        return ["runbook", "minimal"]
    return select_composers(task_type)


def selected_experts(policy: dict[str, Any], task_type: str) -> list[str]:
    if policy["name"] == "mome_auto":
        auto = policy.get("auto_experts_by_task") or {}
        return list(auto.get(task_type) or auto.get("general") or policy.get("experts_enabled") or [])
    return list(policy.get("experts_enabled") or [])


def run_runbook_docs_expert(query: str, db_path: Path, limit: int) -> list[MemoryCandidate]:
    exact: list[MemoryCandidate] = []
    if is_memory_eval_command_query(query):
        exact = exact_memory_eval_runbook_candidates(db_path, max(limit, 20))
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    try:
        terms = [term for term in re.findall(r"[a-z0-9_./-]+", query.lower()) if len(term) > 2]
        where_terms = " OR ".join(["LOWER(mi.text) LIKE ?" for _ in terms]) or "1=1"
        params = tuple(f"%{term}%" for term in terms)
        rows = conn.execute(
            f"""
            SELECT mi.id AS memory_item_id, mi.text, mi.kind, mi.importance, mi.confidence,
                   mi.source_episode_id, mi.source_artifact_path, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE (
                    mi.kind = 'runbook_command'
                    OR LOWER(COALESCE(mi.source_artifact_path,'')) LIKE '%ivy/docs%'
                    OR LOWER(COALESCE(mi.source_artifact_path,'')) LIKE '%ivy/scripts%'
                  )
              AND ({where_terms})
            ORDER BY
                CASE WHEN mi.kind = 'runbook_command' THEN 0 ELSE 1 END,
                mi.created_at DESC,
                mi.id ASC
            LIMIT ?
            """,
            (*params, max(limit, 20)),
        ).fetchall()
        candidates = []
        seen = {c.memory_item_id for c in exact}
        for row in rows:
            d = dict(row)
            if d.get("memory_item_id") in seen:
                continue
            text = str(d.get("text") or "").lower()
            hits = sum(1 for term in terms if term in text)
            d["score"] = float(d.get("importance") or 0.6) + (hits * 0.1)
            candidates.append(candidate_from_result(d, "runbook_docs"))
        for candidate in exact:
            candidate.source_expert = "runbook_docs"
        return exact + candidates
    finally:
        conn.close()


def run_failure_debug_expert(query: str, db_path: Path, limit: int) -> list[MemoryCandidate]:
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    try:
        rows = conn.execute(
            """
            SELECT mi.id AS memory_item_id, mi.text, mi.kind, mi.importance, mi.confidence,
                   mi.source_episode_id, mi.source_artifact_path, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE '%json%'
               OR LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE '%think%'
               OR LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE '%validation%'
               OR LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE '%invalid%'
               OR LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE '%failure%'
            ORDER BY
                CASE
                    WHEN mi.kind = 'json_contamination_warning' THEN 0
                    WHEN LOWER(mi.text) LIKE '%think%' AND LOWER(mi.text) LIKE '%json%' THEN 1
                    WHEN LOWER(mi.text) LIKE '%validation%' THEN 2
                    ELSE 3
                END,
                mi.created_at DESC,
                mi.id DESC
            LIMIT ?
            """,
            (max(limit, 20),),
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            text = str(d.get("text") or "").lower()
            boost = 0.0
            if "think" in text:
                boost += 0.45
            if "json" in text:
                boost += 0.25
            if "validation" in text:
                boost += 0.25
            d["score"] = float(d.get("importance") or 0.7) + boost
            out.append(candidate_from_result(d, "failure_debug"))
        return out
    finally:
        conn.close()


def run_workflow_procedure_expert(query: str, db_path: Path, limit: int) -> list[MemoryCandidate]:
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    try:
        rows = conn.execute(
            """
            SELECT mi.id AS memory_item_id, mi.text, mi.kind, mi.importance, mi.confidence,
                   mi.source_episode_id, mi.source_artifact_path, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE LOWER(mi.kind) LIKE '%workflow%'
               OR LOWER(mi.kind) LIKE '%successful%'
               OR LOWER(mi.text) LIKE '%calc_eval%'
               OR LOWER(mi.text) LIKE '%fs_write%'
               OR LOWER(mi.text) LIKE '%fs_read%'
               OR LOWER(mi.text) LIKE '%json_validate%'
               OR LOWER(mi.text) LIKE '%calc write%'
            ORDER BY
                CASE
                    WHEN LOWER(mi.text) LIKE '%calc_eval%' AND LOWER(mi.text) LIKE '%fs_write%' THEN 0
                    WHEN LOWER(mi.text) LIKE '%fs_read%' AND LOWER(mi.text) LIKE '%json_validate%' THEN 1
                    WHEN LOWER(mi.kind) LIKE '%workflow%' THEN 2
                    ELSE 3
                END,
                mi.created_at DESC,
                mi.id DESC
            LIMIT ?
            """,
            (max(limit, 20),),
        ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            text = str(d.get("text") or "").lower()
            boost = 0.0
            if "calc_eval" in text:
                boost += 0.35
            if "fs_write" in text:
                boost += 0.25
            if "json_validate" in text:
                boost += 0.25
            d["score"] = float(d.get("importance") or 0.7) + boost
            out.append(candidate_from_result(d, "workflow_procedure"))
        return out
    finally:
        conn.close()


def run_mome_expert(expert: str, query: str, db_path: Path, limit: int) -> list[MemoryCandidate]:
    mapped = EXPERT_ALIASES.get(expert, expert)
    if mapped == "runbook_docs":
        return run_runbook_docs_expert(query, db_path, limit)
    if expert == "failure_debug":
        return run_failure_debug_expert(query, db_path, limit)
    if expert == "workflow_procedure":
        return run_workflow_procedure_expert(query, db_path, limit)
    out = run_expert(mapped, query, db_path, limit)
    for candidate in out:
        candidate.source_expert = expert
    return out


def score_candidate(
    query: str,
    task_type: str,
    candidate: MemoryCandidate,
    policy: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    expert_weights = policy.get("expert_weights") or {}
    source_family_weights = policy.get("source_family_weights") or {}
    exact_weights = policy.get("exact_match_weights") or {}
    base_score = float(candidate.score or 0.0)
    expert_score = float(expert_weights.get(candidate.source_expert, 0.0))
    family = candidate.source_family or classify_source_family(candidate)
    source_score = float(source_family_weights.get(family, 0.0))
    concept_score, matched_terms, notes = concept_matches(query, candidate)
    term_score = exact_term_bonus(query, candidate)
    exact_score = (concept_score + term_score) * float(exact_weights.get("default", 1.0))
    for term in matched_terms:
        exact_score += float(exact_weights.get(term, 0.0))
    provenance_score = 0.25 if candidate.provenance_present else -0.35
    task_score = task_type_bonus(task_type, candidate) * float(exact_weights.get("task_type_bonus", 0.25))
    wrong_penalty, wrong_notes = wrong_command_family_penalty(query, candidate)
    notes.extend(wrong_notes)
    final_score = round(base_score + expert_score + source_score + exact_score + provenance_score + task_score - wrong_penalty, 6)
    ranking = {
        "mome_base_score": round(base_score, 6),
        "mome_expert_score": round(expert_score, 6),
        "mome_source_family_score": round(source_score, 6),
        "mome_exact_match_score": round(exact_score, 6),
        "mome_provenance_score": round(provenance_score, 6),
        "mome_task_type_score": round(task_score, 6),
        "mome_penalty": round(wrong_penalty, 6),
        "final_score": final_score,
        "matched_terms": sorted(set(matched_terms)),
        "ranking_notes": notes,
    }
    return final_score, ranking


def route_mome(
    query: str,
    db_path: str | Path | None = None,
    policy_name: str | None = None,
    top_k: int | None = None,
    max_packet_chars: int | None = None,
    require_provenance: bool | None = None,
) -> MomeRouteResult:
    start = time.perf_counter()
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    policy_obj: MomePolicy = load_mome_policy(policy_name)
    policy = policy_obj.document
    task_type = classify_mome_task(query)
    experts = selected_experts(policy, task_type)
    if "none" in experts:
        experts = ["none"]
    per_expert = int(policy.get("max_candidates_per_expert") or top_k or 5)
    max_total = int(policy.get("max_total_candidates") or max((top_k or 5) * 3, 5))
    effective_top_k = int(top_k or policy.get("default_top_k") or 5)
    max_chars = int(max_packet_chars or policy.get("max_packet_chars") or 1800)
    require_prov = bool(policy.get("require_provenance", False) if require_provenance is None else require_provenance)

    collected: list[MemoryCandidate] = []
    warnings: list[str] = []
    for expert in experts:
        try:
            collected.extend(run_mome_expert(expert, query, db, per_expert))
        except (sqlite3.Error, OSError, ValueError) as exc:
            warnings.append(f"expert {expert} failed: {exc}")

    deduped: dict[str, MemoryCandidate] = {}
    for candidate in collected:
        if require_prov and not candidate.provenance_present:
            continue
        candidate.source_family = classify_source_family(candidate)
        final_score, ranking = score_candidate(query, task_type, candidate, policy)
        candidate.score = final_score
        candidate.ranking = ranking
        candidate.metadata["mome"] = {
            "policy": policy["name"],
            "task_type": task_type,
            "expert": candidate.source_expert,
            "source_family": candidate.source_family,
            "ranking": ranking,
        }
        key = str(candidate.memory_item_id) if candidate.memory_item_id is not None else f"{candidate.source_expert}:{candidate.text}"
        if key not in deduped or candidate.score > deduped[key].score:
            deduped[key] = candidate

    ranked = sorted(deduped.values(), key=lambda c: (c.score, c.provenance_present), reverse=True)[:max_total]
    decision = RoutingDecision(
        query=query,
        task_type=task_type,
        selected_policy=policy["name"],
        selected_experts=experts,
        selected_composers=select_mome_composers(task_type),
        top_k=effective_top_k,
        max_packet_chars=max_chars,
    )
    expert_counts = Counter(c.source_expert for c in ranked)
    source_family_counts = Counter(c.source_family for c in ranked)
    matched_terms = sorted(
        {
            term
            for candidate in ranked
            for term in (candidate.ranking or {}).get("matched_terms", [])
        }
    )
    metadata = {
        "query": query,
        "task_type": task_type,
        "policy_name": policy["name"],
        "policy_path": str(policy_obj.path),
        "experts_used": experts,
        "expert_contribution_counts": dict(expert_counts),
        "source_family_counts": dict(source_family_counts),
        "exact_match_terms": matched_terms,
        "candidate_count": len(ranked),
        "provenance_candidate_rate": round(sum(1 for c in ranked if c.provenance_present) / len(ranked), 4) if ranked else 0.0,
        "latency_ms": round((time.perf_counter() - start) * 1000.0, 3),
        "warnings": warnings,
        "injection_allowed": bool(policy.get("injection_allowed", False)),
        "caution_rules_applied": list(policy.get("caution_rules") or []),
    }
    return MomeRouteResult(decision=decision, candidates=ranked, policy=policy, metadata=metadata)
