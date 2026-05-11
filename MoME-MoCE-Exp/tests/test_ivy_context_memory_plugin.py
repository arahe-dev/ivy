from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "ivy-context-memory" / "scripts" / "ivy_context_memory.py"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("ivy_context_memory_plugin", PLUGIN_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    result = plugin.query_store(store, query="What did CP28 show about final answer packet formats?")
    assert result["ok"]
    assert result["selected_count"] == 1
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
