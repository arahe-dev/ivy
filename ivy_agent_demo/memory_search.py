from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .memory_store import MemoryStore, utc_now


HASH_VECTOR_DIM = 256
HASH_VECTOR_MODEL = "stdlib-hash-bow-v1"


def _row_to_result(row: Any, score: float | None = None) -> dict[str, Any]:
    return {
        "memory_item_id": row["id"],
        "kind": row["kind"],
        "text": row["text"],
        "score": score,
        "source_episode_id": row["source_episode_id"],
        "run_id": row["run_id"],
        "source_artifact_path": row["source_artifact_path"],
        "status": row["status"],
        "confidence": row["confidence"],
        "importance": row["importance"],
    }


def keyword_search(query: str, db_path: str | Path | None = None, limit: int = 10) -> tuple[list[dict[str, Any]], bool]:
    store = MemoryStore(db_path)
    store.init_schema()
    caps = store.capabilities()
    conn = store.connect()
    try:
        if caps.fts5:
            rows = conn.execute(
                """
                SELECT mi.*, e.run_id, bm25(memory_items_fts) AS rank
                FROM memory_items_fts
                JOIN memory_items mi ON mi.id = memory_items_fts.rowid
                LEFT JOIN episodes e ON e.id = mi.source_episode_id
                WHERE memory_items_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [_row_to_result(row, score=float(row["rank"])) for row in rows], True
        like = f"%{query}%"
        rows = conn.execute(
            """
            SELECT mi.*, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE mi.text LIKE ? OR mi.kind LIKE ? OR e.task_text LIKE ?
            ORDER BY mi.importance DESC, mi.id DESC
            LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()
        return [_row_to_result(row, score=None) for row in rows], False
    finally:
        conn.close()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def hashed_bow_vector(text: str, dim: int = HASH_VECTOR_DIM) -> list[float]:
    counts = Counter(tokenize(text))
    vec = [0.0] * dim
    for token, count in counts.items():
        idx = int.from_bytes(token.encode("utf-8"), "little", signed=False) % dim
        vec[idx] += float(count)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def vectorize_memory_items(db_path: str | Path | None = None, backend: str = "hash_bow") -> int:
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    try:
        rows = conn.execute(
            """
            SELECT id, text FROM memory_items
            WHERE id NOT IN (
                SELECT memory_item_id FROM memory_vectors
                WHERE backend = ? AND embedding_model = ?
            )
            """,
            (backend, HASH_VECTOR_MODEL),
        ).fetchall()
        with conn:
            for row in rows:
                vec = hashed_bow_vector(row["text"])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memory_vectors
                    (memory_item_id, backend, embedding_model, embedding_dim, vector_json, vector_blob, created_at)
                    VALUES (?, ?, ?, ?, ?, NULL, ?)
                    """,
                    (row["id"], backend, HASH_VECTOR_MODEL, len(vec), json.dumps(vec), utc_now()),
                )
        return len(rows)
    finally:
        conn.close()


def vector_search(query: str, db_path: str | Path | None = None, limit: int = 10) -> list[dict[str, Any]]:
    vectorize_memory_items(db_path)
    qvec = hashed_bow_vector(query)
    store = MemoryStore(db_path)
    conn = store.connect()
    try:
        rows = conn.execute(
            """
            SELECT mi.*, e.run_id, mv.vector_json
            FROM memory_vectors mv
            JOIN memory_items mi ON mi.id = mv.memory_item_id
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE mv.backend = ? AND mv.embedding_model = ?
            """,
            ("hash_bow", HASH_VECTOR_MODEL),
        ).fetchall()
        scored = []
        for row in rows:
            vec = json.loads(row["vector_json"])
            scored.append((_row_to_result(row, score=cosine(qvec, vec)), cosine(qvec, vec)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored[:limit]]
    finally:
        conn.close()


def hybrid_search(query: str, db_path: str | Path | None = None, limit: int = 10) -> list[dict[str, Any]]:
    keyword_results, _ = keyword_search(query, db_path, limit=limit)
    vector_results = vector_search(query, db_path, limit=limit)
    store = MemoryStore(db_path)
    conn = store.connect()
    try:
        recent = conn.execute(
            """
            SELECT mi.*, e.run_id
            FROM memory_items mi
            LEFT JOIN episodes e ON e.id = mi.source_episode_id
            WHERE e.success = 1
            ORDER BY mi.id DESC
            LIMIT ?
            """,
            (max(3, limit // 2),),
        ).fetchall()
        recent_results = [_row_to_result(row, score=0.05) for row in recent]
    finally:
        conn.close()

    combined: dict[int, dict[str, Any]] = {}
    for weight, results in ((1.0, keyword_results), (0.7, vector_results), (0.2, recent_results)):
        for rank, item in enumerate(results):
            item_id = item["memory_item_id"]
            base = max(0.0, 1.0 - rank * 0.05)
            score = weight * base
            if item_id not in combined:
                merged = dict(item)
                merged["score"] = score
                merged["retrieval_sources"] = []
                combined[item_id] = merged
            else:
                combined[item_id]["score"] += score
            combined[item_id]["retrieval_sources"].append("hybrid")
    return sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:limit]
