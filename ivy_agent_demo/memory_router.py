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


def classify_source_family(candidate: MemoryCandidate | None = None, row: dict[str, Any] | None = None) -> str:
    row = row or {}
    kind = str((candidate.kind if candidate else row.get("kind")) or "").lower()
    text = str((candidate.text if candidate else row.get("text")) or "").lower()
    path = str((candidate.source_artifact_path if candidate else row.get("source_artifact_path") or row.get("artifact_path")) or "").replace("\\", "/").lower()
    run_id = str((candidate.run_id if candidate else row.get("run_id")) or "").lower()
    blob = f"{kind} {text} {path} {run_id}"
    if "collect_qwen36_metrics.py" in blob:
        return "source_code"
    if "qwen36_4060_bench" in blob or kind == "benchmark_result":
        return "benchmark_artifact"
    if "phase1_agent_demo" in blob or "runs/" in path:
        if any(t in blob for t in ("workflow", "successful", "tool_trace", "tool", "fs_read", "fs_write", "calc_eval")):
            return "workflow_trace"
        return "run_artifact"
    if any(name in path for name in ("policy.py", "validator.py", "tools.py", "schemas.py")):
        if any(t in blob for t in ("safety", "policy", "sandbox", "path", "delete", "network", "write")):
            return "safety_policy"
        return "source_code"
    if kind in {"safety_rule", "policy_rule", "validator_rule"}:
        return "safety_policy"
    if any(t in kind for t in ("workflow", "tool_trace", "successful_pattern", "success")):
        return "workflow_trace"
    if "ivy/scripts" in path or ".ps1" in path or kind == "runbook_command" or "python -m " in text:
        return "runbook"
    if "ivy/docs" in path or "readme" in path or kind == "doc_reference":
        return "doc_memory"
    if "benchmark" in kind:
        return "benchmark_artifact"
    return "unknown"


def candidate_from_result(row: dict[str, Any], expert: str, boost: float = 0.0) -> MemoryCandidate:
    score = row.get("score")
    try:
        numeric = float(score) if score is not None else 0.0
    except Exception:
        numeric = 0.0
    if numeric < 0:
        numeric = 1.0 / (1.0 + abs(numeric))
    candidate = MemoryCandidate(
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
    candidate.source_family = classify_source_family(candidate, row)
    return candidate


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
            ORDER BY
                CASE
                    WHEN mi.kind = 'benchmark_result' THEN 0
                    WHEN mi.kind IN ('safety_rule', 'policy_rule') THEN 1
                    WHEN mi.kind LIKE '%workflow%' OR mi.kind LIKE '%successful%' THEN 2
                    WHEN mi.kind = 'runbook_command' THEN 3
                    ELSE 4
                END,
                mi.created_at DESC, mi.id DESC
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
        safe_query = re.sub(r"[^A-Za-z0-9_]+", " ", query).strip() or query
        rows, _ = keyword_search(safe_query, db_path, limit)
        return [candidate_from_result(r, expert, 0.1) for r in rows]
    if expert == "vector":
        return [candidate_from_result(r, expert) for r in vector_search(query, db_path, limit)]
    if expert == "hybrid":
        safe_query = re.sub(r"[^A-Za-z0-9_]+", " ", query).strip() or query
        return [candidate_from_result(r, expert, 0.15) for r in hybrid_search(safe_query, db_path, limit)]
    if expert == "recent":
        return _direct_query(db_path, "1=1", (), expert, limit)
    if expert == "failure":
        like = "%failed%|%failure%|%invalid%|%rejected%|%policy%|%error%|%think%|%json%"
        terms = [t for t in like.split("|")]
        where = " OR ".join(["LOWER(mi.text || ' ' || COALESCE(mi.kind,'')) LIKE ?" for _ in terms])
        return _direct_query(db_path, where, tuple(terms), expert, limit)
    if expert == "benchmark":
        terms = ("%qwen36_4060_bench%", "%benchmark_result%", "%decode_tps%", "%ctx=%")
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


def normalized_query_terms(query: str) -> set[str]:
    q = query.lower()
    terms = set(re.findall(r"[a-z0-9_=.]+", q))
    if re.search(r"\bctx\s+512\b", q):
        terms.add("ctx=512")
    if re.search(r"\bn[_ -]?gpu[_ -]?layers\b", q):
        terms.add("n_gpu_layers")
    if "cache k" in q:
        terms.add("cache_k")
    if "cache v" in q:
        terms.add("cache_v")
    return terms


def concept_matches(query: str, candidate: MemoryCandidate) -> tuple[float, list[str], list[str]]:
    q = query.lower()
    blob = f"{candidate.text} {candidate.kind or ''} {candidate.source_artifact_path or ''}".lower()
    matched: list[str] = []
    notes: list[str] = []
    score = 0.0
    is_preview_command = candidate.source_family == "runbook" and "memory_packet_cli preview" in blob

    exact_terms = sorted(normalized_query_terms(query))
    for term in exact_terms:
        aliases = [term]
        if term == "512":
            aliases.append("ctx=512")
        if term == "ctx":
            aliases.extend(["ctx=512", "ctx_size"])
        if term in {"validate", "validation"}:
            aliases.extend(["json_validate", "validation"])
        if any(alias in blob for alias in aliases):
            matched.append(term)
            score += 0.02 if is_preview_command else 0.08

    concepts = [
        ("ctx=512", ["ctx=512", "ctx 512"], ["ctx=512"]),
        ("decode_tps", ["decode_tps"], ["decode_tps"]),
        ("n_gpu_layers", ["n_gpu_layers", "gpu layers"], ["n_gpu_layers"]),
        ("cache_k", ["cache_k"], ["cache_k"]),
        ("cache_v", ["cache_v"], ["cache_v"]),
        ("cpu_moe", ["cpu_moe"], ["cpu_moe"]),
        ("write_outside_sandbox", ["write outside sandbox"], ["write", "outside", "sandbox", "path_outside_sandbox"]),
        ("path_traversal", ["path traversal"], ["path", "traversal"]),
        ("absolute_path", ["absolute path"], ["absolute", "path", "is_absolute"]),
        ("unsafe_delete", ["unsafe delete", "delete"], ["delete", "remove", "wipe"]),
        ("network_block", ["network"], ["network", "http", "ftp"]),
        ("sandbox_relative", ["sandbox relative", "sandbox-relative"], ["sandbox", "relative"]),
        ("fs_read", ["fs_read"], ["fs_read"]),
        ("json_validate", ["json_validate", "json validate"], ["json_validate", "validate"]),
        ("fs_write", ["fs_write"], ["fs_write"]),
        ("calc_eval", ["calc_eval"], ["calc_eval"]),
        ("memory_eval", ["memory eval", "memory_eval"], ["memory_eval"]),
        ("packet_sweep", ["packet sweep", "memory_packet_sweep"], ["memory_packet_sweep"]),
        ("phase1_agent_demo", ["phase1_agent_demo"], ["phase1_agent_demo"]),
        ("qwen_bench_ingest", ["qwen benchmark", "qwen36_4060_bench"], ["qwen36_4060_bench"]),
    ]
    for name, q_needles, c_needles in concepts:
        if any(needle in q for needle in q_needles) and all(needle in blob for needle in c_needles[: min(2, len(c_needles))]):
            matched.append(name)
            score += 0.35
            notes.append(f"exact concept match: {name}")

    return min(score, 2.0), sorted(set(matched)), notes


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


SOURCE_PRIORS = {
    "benchmark": {
        "benchmark_artifact": 1.2,
        "run_artifact": 0.45,
        "runbook": 0.2,
        "doc_memory": -0.1,
        "source_code": -0.35,
        "safety_policy": -0.4,
        "workflow_trace": -0.1,
    },
    "safety": {
        "safety_policy": 1.0,
        "source_code": 0.55,
        "run_artifact": 0.35,
        "workflow_trace": 0.15,
        "doc_memory": 0.1,
        "runbook": -0.1,
        "benchmark_artifact": -0.5,
    },
    "workflow": {
        "workflow_trace": 1.0,
        "run_artifact": 0.45,
        "runbook": 0.25,
        "doc_memory": 0.0,
        "safety_policy": 0.1,
        "benchmark_artifact": -0.4,
    },
    "tool_debug": {
        "run_artifact": 0.75,
        "benchmark_artifact": 0.55,
        "safety_policy": 0.35,
        "runbook": 0.0,
        "doc_memory": -0.2,
        "source_code": 0.1,
    },
    "planning": {
        "doc_memory": 0.75,
        "runbook": 0.6,
        "source_code": 0.2,
        "run_artifact": 0.0,
        "benchmark_artifact": -0.25,
    },
    "general": {
        "doc_memory": 0.55,
        "runbook": 0.5,
        "source_code": 0.25,
        "run_artifact": 0.0,
        "benchmark_artifact": -0.15,
    },
}


def source_family_score(task_type: str, candidate: MemoryCandidate, policy: dict[str, Any]) -> float:
    family = candidate.source_family or "unknown"
    score = SOURCE_PRIORS.get(task_type, SOURCE_PRIORS["general"]).get(family, 0.0)
    if task_type == "benchmark" and family == "runbook" and "memory_packet_cli preview" in candidate.text.lower():
        score -= 0.8
    score += float((policy.get("source_family_weights") or {}).get(family, 0.0))
    field_map = {
        "benchmark_artifact": "benchmark_artifact_bonus",
        "safety_policy": "safety_policy_bonus",
        "workflow_trace": "workflow_trace_bonus",
        "runbook": "runbook_bonus",
        "source_code": "source_code_bonus",
        "doc_memory": "doc_memory_penalty",
    }
    field = field_map.get(family)
    if field and field in policy:
        value = float(policy.get(field) or 0.0)
        score += -abs(value) if field == "doc_memory_penalty" else value
    return score


def route_memory(
    query: str,
    db_path: str | Path | None = None,
    policy_name: str | None = None,
    top_k: int | None = None,
    max_packet_chars: int | None = None,
    require_provenance: bool | None = None,
) -> tuple[RoutingDecision, list[MemoryCandidate], dict[str, Any]]:
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
        base_score = candidate.score * float(weights.get("base_score", 1.0))
        score = base_score
        provenance_score = 0.0
        if candidate.provenance_present:
            provenance_score = float(weights.get("provenance_bonus", 0.25))
            score += provenance_score
        else:
            provenance_score = -float(weights.get("missing_provenance_penalty", 0.4))
            score += provenance_score
        exact_match_score, matched_terms, notes = concept_matches(query, candidate)
        exact_match_score += exact_term_bonus(query, candidate) * float(weights.get("exact_term_bonus", 0.2))
        exact_match_score *= float(policy.get("exact_match_bonus", 1.0))
        source_score = source_family_score(task_type, candidate, policy)
        task_score = task_type_bonus(task_type, candidate) * float(weights.get("task_type_bonus", 0.2))
        duplicate_penalty = 0.0
        score += exact_match_score + source_score + task_score - duplicate_penalty
        final_score = round(score, 6)
        candidate.ranking = {
            "source_family": candidate.source_family,
            "base_score": round(base_score, 6),
            "exact_match_score": round(exact_match_score, 6),
            "source_family_score": round(source_score, 6),
            "provenance_score": round(provenance_score, 6),
            "task_type_score": round(task_score, 6),
            "duplicate_penalty": round(duplicate_penalty, 6),
            "final_score": final_score,
            "matched_terms": matched_terms,
            "ranking_notes": notes,
        }
        candidate.metadata["ranking"] = candidate.ranking
        candidate.metadata["source_family"] = candidate.source_family
        candidate.score = final_score
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
    return decision, ranked[: max(effective_top_k * 3, effective_top_k)], policy
