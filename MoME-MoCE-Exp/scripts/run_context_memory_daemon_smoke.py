from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
PLUGIN_SCRIPT = REPO_ROOT / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"
DEFAULT_STORE = ROOT / "out" / "daemon_smoke_store"
DEFAULT_OUT = ROOT / "docs" / "DAEMON_SMOKE_TEST.md"
DEFAULT_SOURCE_ROOT = ROOT

WARM_QUERIES = [
    "What did CP28 show about final answer packet formats?",
    "What MCP tools does ivy-context-memory expose?",
    "What is the latest CP42 rebuild policy versus stale memory?",
    "What is today's Bitcoin price?",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request_json(url: str, *, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310 - localhost-only smoke test
        return json.loads(response.read().decode("utf-8"))


def wait_health(base_url: str, *, timeout_s: float = 10.0) -> dict[str, Any]:
    deadline = time.perf_counter() + timeout_s
    last_error = ""
    while time.perf_counter() < deadline:
        try:
            return request_json(f"{base_url}/health", timeout=1.0)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = str(exc)
            time.sleep(0.1)
    raise RuntimeError(f"daemon did not become healthy: {last_error}")


def daemon_checks(result: dict[str, Any], *, max_query_wall_ms: float, max_router_ms: float) -> dict[str, Any]:
    warm = result.get("warm_summary", {})
    caches = result.get("status_process_caches", {})
    query = result.get("query_summary", {})
    hook = result.get("agent_hook_summary", {})
    packet = result.get("packet_v2_summary", {})
    ingest = result.get("ingest_summary", {})
    checks = {
        "health_ok": bool(result.get("health", {}).get("ok")),
        "ingest_has_corpus": int(ingest.get("corpus_items", 0) or 0) >= 1,
        "warm_ok": int(warm.get("warmed_queries", 0) or 0) >= 1,
        "query_index_cache_warm": int(caches.get("query_index_cache_entries", 0) or 0) >= 1,
        "item_feature_cache_warm": int(caches.get("item_feature_cache_entries", 0) or 0) >= 1,
        "corpus_item_cache_warm": int(caches.get("corpus_item_cache_entries", 0) or 0) >= 1,
        "query_selected_evidence": bool(query.get("selected_ids")),
        "agent_hook_selected_evidence": bool(hook.get("selected_ids")),
        "packet_v2_selected_evidence": bool(packet.get("selected_ids")),
        "query_wall_under_budget": float(query.get("wall_ms") or 0.0) <= max_query_wall_ms,
        "router_under_budget": float(query.get("latency_ms") or 0.0) <= max_router_ms,
    }
    return {"passed": all(checks.values()), "checks": checks, "max_query_wall_ms": max_query_wall_ms, "max_router_ms": max_router_ms}


def run_daemon_smoke(store: Path, *, source_root: Path, port: int | None = None, max_query_wall_ms: float = 15.0, max_router_ms: float = 5.0) -> dict[str, Any]:
    started = time.perf_counter()
    chosen_port = port or free_port()
    base_url = f"http://127.0.0.1:{chosen_port}"
    store.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            str(PLUGIN_SCRIPT),
            "--store",
            str(store),
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(chosen_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        health = wait_health(base_url)
        ingest = request_json(f"{base_url}/ingest", payload={"source_root": str(source_root), "build": True}, timeout=60.0)
        warm = request_json(f"{base_url}/warm", payload={"queries": WARM_QUERIES}, timeout=60.0)
        status = request_json(f"{base_url}/status", timeout=10.0)
        query = request_json(f"{base_url}/query", payload={"query": "What did CP28 show about final answer packet formats?"}, timeout=20.0)
        agent_hook = request_json(
            f"{base_url}/agent/hook",
            payload={"hook": "before_task", "task": "What did CP28 show about final answer packet formats?"},
            timeout=20.0,
        )
        packet_v2 = request_json(
            f"{base_url}/packet/v2",
            payload={"query": "What MCP tools does ivy-context-memory expose?", "hook": "before_edit"},
            timeout=20.0,
        )
        caches = status.get("process_caches", {})
        result = {
            "schema_version": "ivy_context_memory.daemon_smoke.v0.1",
            "created_at": utc_now(),
            "base_url": base_url,
            "store": str(store),
            "source_root": str(source_root),
            "wall_ms": round((time.perf_counter() - started) * 1000, 3),
            "health": health,
            "ingest_summary": ingest.get("build", ingest),
            "warm_summary": {
                "warmed_queries": warm.get("warmed_queries"),
                "index_items": warm.get("index_items"),
                "query_index_cache_entries": warm.get("query_index_cache_entries"),
                "item_feature_cache_entries": warm.get("item_feature_cache_entries"),
                "corpus_item_cache_entries": warm.get("corpus_item_cache_entries"),
                "wall_ms": warm.get("wall_ms"),
            },
            "status_process_caches": caches,
            "query_summary": {
                "selected_ids": query.get("selected_ids", []),
                "packet_mode": query.get("packet_mode"),
                "wall_ms": query.get("wall_ms"),
                "latency_ms": query.get("latency_ms"),
                "timings_ms": query.get("timings_ms", {}),
            },
            "agent_hook_summary": {
                "schema_version": agent_hook.get("schema_version"),
                "hook": agent_hook.get("hook"),
                "selected_ids": agent_hook.get("packet", {}).get("selected_ids", []),
                "packet_mode": agent_hook.get("packet", {}).get("mode"),
            },
            "packet_v2_summary": {
                "schema_version": packet_v2.get("schema_version"),
                "hook": packet_v2.get("hook"),
                "selected_ids": packet_v2.get("packet", {}).get("selected_ids", []),
                "packet_mode": packet_v2.get("packet", {}).get("mode"),
            },
        }
        result["status"] = daemon_checks(result, max_query_wall_ms=max_query_wall_ms, max_router_ms=max_router_ms)
        result["passed"] = result["status"]["passed"]
        return result
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def write_report(result: dict[str, Any], out: Path) -> None:
    warm = result["warm_summary"]
    query = result["query_summary"]
    hook = result.get("agent_hook_summary", {})
    packet = result.get("packet_v2_summary", {})
    lines = [
        "# IVY Context Memory Daemon Smoke Test",
        "",
        f"Created: `{result['created_at']}`",
        f"Passed: `{result['passed']}`",
        f"Base URL: `{result['base_url']}`",
        f"Total wall: `{result['wall_ms']} ms`",
        f"Query wall budget: `{result['status']['max_query_wall_ms']} ms`",
        f"Router budget: `{result['status']['max_router_ms']} ms`",
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for name, passed in result["status"]["checks"].items():
        lines.append(f"| `{name}` | `{passed}` |")
    lines.extend(
        [
            "",
        "## Warmup",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Warmed queries | `{warm.get('warmed_queries')}` |",
        f"| Index items | `{warm.get('index_items')}` |",
        f"| Query index cache entries | `{warm.get('query_index_cache_entries')}` |",
        f"| Item feature cache entries | `{warm.get('item_feature_cache_entries')}` |",
        f"| Corpus item cache entries | `{warm.get('corpus_item_cache_entries')}` |",
        f"| Warm wall | `{warm.get('wall_ms')} ms` |",
        "",
        "## Query",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Selected | `{', '.join(query.get('selected_ids', []))}` |",
        f"| Packet mode | `{query.get('packet_mode')}` |",
        f"| Query wall | `{query.get('wall_ms')} ms` |",
        f"| Router latency | `{query.get('latency_ms')} ms` |",
        "",
        "## Agent Hooks",
        "",
        "| Surface | Hook | Selected | Packet mode |",
        "|---|---|---:|---|",
        f"| `/agent/hook` | `{hook.get('hook')}` | `{', '.join(hook.get('selected_ids', []))}` | `{hook.get('packet_mode')}` |",
        f"| `/packet/v2` | `{packet.get('hook')}` | `{', '.join(packet.get('selected_ids', []))}` | `{packet.get('packet_mode')}` |",
        "",
        "## Timing Breakdown",
        "",
        "| Stage | ms |",
        "|---|---:|",
        ]
    )
    for name, value in query.get("timings_ms", {}).items():
        lines.append(f"| `{name}` | `{value}` |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the IVY context-memory HTTP daemon and smoke-test warm/query/status.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--max-query-wall-ms", type=float, default=15.0)
    parser.add_argument("--max-router-ms", type=float, default=5.0)
    args = parser.parse_args()

    result = run_daemon_smoke(
        args.store.resolve(),
        source_root=args.source_root.resolve(),
        port=args.port,
        max_query_wall_ms=args.max_query_wall_ms,
        max_router_ms=args.max_router_ms,
    )
    write_report(result, args.out.resolve())
    print(json.dumps({"ok": True, "passed": result["passed"], "report": str(args.out), "summary": result}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
