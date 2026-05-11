from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


PLUGIN_SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def framed(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def parse_framed_messages(blob: bytes) -> list[dict]:
    messages = []
    offset = 0
    while offset < len(blob):
        header_end = blob.index(b"\r\n\r\n", offset)
        headers = blob[offset:header_end].decode("ascii")
        length = 0
        for line in headers.splitlines():
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
        body_start = header_end + 4
        body_end = body_start + length
        messages.append(json.loads(blob[body_start:body_end].decode("utf-8")))
        offset = body_end
    return messages


def test_plugin_remember_build_query_roundtrip(tmp_path: Path) -> None:
    plugin = load_plugin_module()
    store = tmp_path / "store"
    init = plugin.init_store(store)
    assert init["ok"]

    remembered = plugin.remember(
        store,
        text="CP28 showed contradiction-aware packets won final-answer A/B on conflict cases.",
        source_path="root/notes/cp28.md",
        tags=["cp28", "final-answer"],
        authority="medium",
    )
    assert remembered["ok"]
    assert remembered["build"]["corpus_items"] == 1
    assert remembered["build"]["index"]["items"] == 1

    result = plugin.query_store(store, query="What did CP28 show about final answer packet formats?")
    assert result["ok"]
    assert result["selected_count"] == 1
    assert result["prefilter"]["enabled"] is True
    assert result["prefilter"]["candidate_count"] == 1
    assert "contradiction-aware" in result["packet_text"].lower()
    assert result["query"] == "What did CP28 show about final answer packet formats?"


def test_plugin_rejects_secret_like_note(tmp_path: Path) -> None:
    plugin = load_plugin_module()
    store = tmp_path / "store"
    plugin.init_store(store)
    try:
        plugin.remember(
            store,
            text="api key token should not enter memory",
            source_path="root/notes/secret.md",
            tags=["secret"],
        )
        raise AssertionError("secret-like notes should be rejected")
    except ValueError as exc:
        assert "secret" in str(exc).lower()


def test_plugin_ingest_skips_generated_outputs(tmp_path: Path) -> None:
    plugin = load_plugin_module()
    source = tmp_path / "source"
    (source / "out").mkdir(parents=True)
    (source / "README.md").write_text("CP29 source memory should be visible to the plugin query index.", encoding="utf-8")
    (source / "out" / "generated.md").write_text("Generated output should not be indexed as live source memory.", encoding="utf-8")

    store = tmp_path / "store"
    added = plugin.add_source(store, source, build=True)

    assert added["build"]["corpus_items"] == 1
    assert added["build"]["index"]["items"] == 1


def test_direct_agent_note_can_beat_generic_source_doc(tmp_path: Path) -> None:
    plugin = load_plugin_module()
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text(
        "CP28 final answer packet formats are mentioned in this generic project runbook.",
        encoding="utf-8",
    )

    store = tmp_path / "store"
    plugin.add_source(store, source, build=False)
    plugin.remember(
        store,
        text="CP28 showed contradiction-aware packets won final-answer A/B on conflict cases.",
        source_path="root/notes/cp28.md",
        tags=["cp28", "final-answer"],
        authority="medium",
    )
    result = plugin.query_store(store, query="What did CP28 show about final answer packet formats?")

    assert result["selected_ids"][0].startswith("note_")
    assert result["variant"] == result["packet_mode"]


def test_repeated_build_uses_fingerprint_cache(tmp_path: Path) -> None:
    plugin = load_plugin_module()
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("CP32 cache source memory should build once and then reuse.", encoding="utf-8")

    store = tmp_path / "store"
    first = plugin.add_source(store, source, build=True)
    second = plugin.build_store(store)

    assert first["build"]["cache"]["status"] == "miss"
    assert second["cache"]["status"] == "hit"
    assert second["corpus_items"] == first["build"]["corpus_items"]


def test_mcp_stdio_lists_and_calls_status(tmp_path: Path) -> None:
    store = tmp_path / "store"
    payload = b"".join(
        [
            framed({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            framed({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            framed({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ivy_memory_status", "arguments": {}}}),
        ]
    )

    proc = subprocess.run(
        [sys.executable, str(PLUGIN_SCRIPT), "--store", str(store), "mcp"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    messages = parse_framed_messages(proc.stdout)

    assert messages[0]["result"]["serverInfo"]["name"] == "ivy-context-memory"
    tool_names = {tool["name"] for tool in messages[1]["result"]["tools"]}
    assert {"ivy_memory_query", "ivy_memory_remember", "ivy_memory_status"} <= tool_names
    assert messages[2]["result"]["structuredContent"]["ok"] is True


def test_mcp_stdio_remember_then_query(tmp_path: Path) -> None:
    store = tmp_path / "store"
    payload = b"".join(
        [
            framed({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            framed(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "ivy_memory_remember",
                        "arguments": {
                            "text": "CP35 proves MCP clients can remember and query IVY memory in one session.",
                            "source_path": "root/notes/cp35.md",
                            "tags": ["cp35", "mcp"],
                        },
                    },
                }
            ),
            framed(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "ivy_memory_query",
                        "arguments": {"query": "What does CP35 prove about MCP clients?"},
                    },
                }
            ),
        ]
    )

    proc = subprocess.run(
        [sys.executable, str(PLUGIN_SCRIPT), "--store", str(store), "mcp"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    messages = parse_framed_messages(proc.stdout)
    remembered = messages[1]["result"]["structuredContent"]
    queried = messages[2]["result"]["structuredContent"]

    assert remembered["ok"] is True
    assert queried["ok"] is True
    assert queried["selected_ids"][0].startswith("note_")
    assert "CP35 proves MCP clients" in queried["packet_text"]
