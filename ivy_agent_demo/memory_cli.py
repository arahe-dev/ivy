from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .memory_ingest import ingest_run_dir, ingest_runs_root
from .memory_search import hybrid_search, keyword_search, vector_search, vectorize_memory_items
from .memory_store import DEFAULT_DB_PATH, MemoryStore


def emit(payload: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif isinstance(payload, list):
        for item in payload:
            print(f"[{item.get('memory_item_id')}] {item.get('kind')} score={item.get('score')}")
            print(f"  {item.get('text')}")
            print(f"  run={item.get('run_id')} artifact={item.get('source_artifact_path')} status={item.get('status')}")
    elif isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    else:
        print(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="IVY passive memory CLI")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite memory DB path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--json", action="store_true")

    p_ingest = sub.add_parser("ingest")
    group = p_ingest.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-dir")
    group.add_argument("--runs-root")
    p_ingest.add_argument("--json", action="store_true")

    p_search = sub.add_parser("search")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--json", action="store_true")

    p_vec = sub.add_parser("vector-search")
    p_vec.add_argument("--query", required=True)
    p_vec.add_argument("--limit", type=int, default=10)
    p_vec.add_argument("--json", action="store_true")

    p_hybrid = sub.add_parser("hybrid-search")
    p_hybrid.add_argument("--query", required=True)
    p_hybrid.add_argument("--limit", type=int, default=10)
    p_hybrid.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats")
    p_stats.add_argument("--json", action="store_true")

    args = parser.parse_args()
    db = Path(args.db)
    store = MemoryStore(db)

    if args.cmd == "init":
        caps = store.init_schema()
        emit({"db": str(db), "fts5_available": caps.fts5, "sqlite_vec_available": caps.sqlite_vec}, args.json)
    elif args.cmd == "ingest":
        if args.run_dir:
            counts = ingest_run_dir(args.run_dir, db)
        else:
            counts = ingest_runs_root(args.runs_root, db)
        vectorized = vectorize_memory_items(db)
        counts["vectorized"] = vectorized
        emit(counts, args.json)
    elif args.cmd == "search":
        rows, used_fts = keyword_search(args.query, db, args.limit)
        if not args.json and not used_fts:
            print("Warning: FTS5 unavailable; used LIKE fallback.")
        emit(rows, args.json)
    elif args.cmd == "vector-search":
        emit(vector_search(args.query, db, args.limit), args.json)
    elif args.cmd == "hybrid-search":
        emit(hybrid_search(args.query, db, args.limit), args.json)
    elif args.cmd == "stats":
        store.init_schema()
        emit(store.stats(), args.json)


if __name__ == "__main__":
    main()
