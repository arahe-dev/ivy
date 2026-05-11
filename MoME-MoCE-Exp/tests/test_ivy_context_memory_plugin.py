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
