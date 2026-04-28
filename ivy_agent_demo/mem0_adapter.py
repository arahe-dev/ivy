from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .memory_store import DEFAULT_DB_PATH, MemoryStore


MEM0_AVAILABLE = False

try:
    import mem0

    MEM0_AVAILABLE = True
except ImportError:
    pass


def get_mem0_client() -> Any | None:
    if not MEM0_AVAILABLE:
        return None
    try:
        return __import__("mem0").Memory.from_llm()
    except Exception:
        try:
            return __import__("mem0").Memory()
        except Exception:
            return None


def status() -> dict[str, Any]:
    if not MEM0_AVAILABLE:
        return {"available": False, "message": "Mem0 not installed. Install with: pip install mem0"}
    client = get_mem0_client()
    if client is None:
        return {"available": False, "message": "Mem0 client initialization failed"}
    return {"available": True, "message": "Mem0 is available"}


def ingest_from_ivy(db_path: Path, limit: int = 100) -> dict[str, Any]:
    if not MEM0_AVAILABLE:
        return {"added": 0, "message": "Mem0 not installed"}
    client = get_mem0_client()
    if client is None:
        return {"added": 0, "message": "Mem0 client init failed"}
    store = MemoryStore(db_path)
    store.init_schema()
    conn = store.connect()
    added = 0
    try:
        with conn:
            cursor = conn.execute(
                """
                SELECT memory_item_id, text, kind, source_artifact_path, run_id, source_episode_id
                FROM memory_items
                WHERE status = 'active'
                ORDER BY importance DESC, confidence DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            for row in rows:
                memory_item_id, text, kind, source_artifact_path, run_id, source_episode_id = row
                if not text or len(text) > 2000:
                    continue
                if "password" in text.lower() or "api_key" in text.lower():
                    continue
                try:
                    client.add(
                        text[:2000],
                        metadata={
                            "memory_item_id": memory_item_id,
                            "kind": kind,
                            "source_artifact_path": source_artifact_path or "",
                            "run_id": run_id or "",
                            "source_episode_id": source_episode_id or "",
                        },
                    )
                    added += 1
                except Exception:
                    pass
    finally:
        conn.close()
    return {"added": added, "total": len(rows)}


def search_mem0(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not MEM0_AVAILABLE:
        return []
    client = get_mem0_client()
    if client is None:
        return []
    try:
        results = client.search(query, limit=limit)
        return [
            {
                "text": r.get("memory", r.get("text", "")),
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ]
    except Exception:
        return []


def build_packet_from_mem0(
    query: str, max_chars: int = 800
) -> dict[str, Any]:
    results = search_mem0(query, limit=5)
    if not results:
        return {"packet_text": "", "empty": True, "available": False}
    lines = []
    provenance = 0
    for r in results:
        text = r.get("text", "")[:150]
        metadata = r.get("metadata", {})
        if metadata.get("source_artifact_path"):
            provenance += 1
        lines.append(f"- Imported memory: {text}...")
    packet_text = "\n".join(lines)
    if len(packet_text) > max_chars:
        packet_text = packet_text[:max_chars] + "..."
    return {
        "packet_text": packet_text,
        "empty": not packet_text.strip(),
        "available": True,
        "provenance_present": provenance > 0,
        "evidence_count": len(results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Mem0 adapter for IVY memory.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Check Mem0 availability")
    ing = sub.add_parser("ingest-from-ivy", help="Ingest from IVY SQLite to Mem0")
    ing.add_argument("--db", default=str(DEFAULT_DB_PATH))
    ing.add_argument("--limit", type=int, default=100)
    sr = sub.add_parser("search", help="Search Mem0")
    sr.add_argument("--query", required=True)
    sr.add_argument("--limit", type=int, default=5)
    pkt = sub.add_parser("packet", help="Build packet from Mem0")
    pkt.add_argument("--query", required=True)
    pkt.add_argument("--max-chars", type=int, default=800)
    args = parser.parse_args()
    if args.command == "status" or args.command is None:
        print(json.dumps(status(), indent=2))
        return
    if args.command == "ingest-from-ivy":
        result = ingest_from_ivy(Path(args.db), args.limit)
        print(json.dumps(result, indent=2))
        return
    if args.command == "search":
        results = search_mem0(args.query, args.limit)
        print(json.dumps(results, indent=2))
        return
    if args.command == "packet":
        result = build_packet_from_mem0(args.query, args.max_chars)
        print(json.dumps(result, indent=2))
        return


if __name__ == "__main__":
    main()