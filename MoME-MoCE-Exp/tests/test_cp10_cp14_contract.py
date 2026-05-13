from __future__ import annotations

import json
import sys
from pathlib import Path

IVY_ROOT = Path(__file__).resolve().parents[2]
if str(IVY_ROOT) not in sys.path:
    sys.path.insert(0, str(IVY_ROOT))

from ivy_agent_demo.acca_context import route_context
from ivy_agent_demo.acca_corpus_export import export_acca_corpus
from ivy_agent_demo.acca_milestone_ingest import build_milestone_record
from ivy_agent_demo.agent_loop import _prepare_acca_context
from ivy_agent_demo.memory_store import MemoryStore
from scripts.run_answer_level_eval import run_eval
from scripts.generate_ivy_real_v3_dataset import write_dataset
from scripts.memory_write_barrier import MemoryWriteError, append_memory_record, validate_memory_record
from scripts.run_latency_gate import run_latency_gate
from scripts.run_provider_certification_matrix import certification_decision
from scripts.mome_moce_harness import OpenCodeGoFinder, MoMEMoCERouter, benchmark, load_cases, load_corpus


ROOT = Path(__file__).resolve().parents[1]
IVY_REAL_V2 = ROOT / "out" / "context_stress_ivy_real_v2"


def test_cp10_answer_level_eval_prefers_d_acca() -> None:
    payload = run_eval(IVY_REAL_V2, backend="indexed", naive_top_k=5, limit=24)
    summary = payload["summary"]
    assert summary["d_acca"]["quality"] >= 0.9
    assert summary["d_acca"]["quality"] >= summary["naive_bm25"]["quality"]
    assert summary["d_acca"]["quality"] > summary["no_context"]["quality"]


def test_cp11_ivy_real_v3_generator_adds_hard_cases(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_stress_ivy_real_v3"
    payload = write_dataset(IVY_REAL_V2, out_dir)
    assert payload["hard_cases"] >= 5
    cases = load_cases(out_dir)
    assert len(cases) == payload["cases"]
    router = MoMEMoCERouter(load_corpus(out_dir), candidate_backend="indexed", dataset_path=out_dir)
    summary = benchmark(router, cases, validate_artifacts=False)
    assert summary["quality"] >= 0.9
    assert summary["evidence_metrics"]["forbidden_hits"] == 0


def test_cp12_latency_gate_passes_sub_5ms_p50(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_stress_ivy_real_v3"
    write_dataset(IVY_REAL_V2, out_dir)
    payload = run_latency_gate(out_dir, max_mean_ms=5.0, max_p50_ms=5.0, max_worst_ms=25.0)
    assert payload["passed"]
    assert payload["summary"]["latency_ms"]["p50"] <= 5.0
    assert payload["summary"]["evidence_metrics"]["forbidden_hits"] == 0


def test_cp15_ivy_real_v3_hard_cases_are_solved(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_stress_ivy_real_v3"
    write_dataset(IVY_REAL_V2, out_dir)
    router = MoMEMoCERouter(load_corpus(out_dir), candidate_backend="indexed", dataset_path=out_dir)
    summary = benchmark(router, load_cases(out_dir), validate_artifacts=False)
    assert summary["passed"] == summary["cases"]
    assert summary["evidence_metrics"]["forbidden_hits"] == 0
    assert summary["latency_ms"]["p50"] <= 5.0


def test_cp16_acca_context_bridge_renders_prompt_packet(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_stress_ivy_real_v3"
    write_dataset(IVY_REAL_V2, out_dir)
    result = route_context(
        "That recurring prefix thing for hot sessions: what rule keeps reuse from breaking?",
        dataset=out_dir,
    )
    assert result.selected_ids == ["doc_hot_session_cache_rule"]
    assert "ACCA CONTEXT PACKET" in result.context_text
    assert "doc_hot_session_cache_rule" in result.context_text
    assert result.latency_ms <= 10.0


def test_cp17_exports_runtime_memory_to_acca_corpus(tmp_path: Path) -> None:
    db = tmp_path / "ivy_memory.sqlite3"
    store = MemoryStore(db)
    store.init_schema()
    episode_id = store.insert_episode(run_id="cp17-test", task_text="test task", outcome="passed", success=True)
    conn = store.connect()
    try:
        with conn:
            store.insert_memory_item(
                conn,
                source_episode_id=episode_id,
                kind="policy_warning",
                text="Policy blocked an absolute path read outside sandbox.",
                confidence=0.95,
                source_artifact_path=str(IVY_ROOT / "runs" / "example" / "run_summary.json"),
            )
    finally:
        conn.close()
    manifest = export_acca_corpus(db, tmp_path / "acca_export")
    corpus_path = tmp_path / "acca_export" / "corpus" / "corpus_items.jsonl"
    rows = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines()]
    assert manifest["corpus_items"] == 1
    assert rows[0]["source_family"] == "safety_policy"
    assert rows[0]["authority"] == "high"
    assert rows[0]["provenance"]["artifact_path"] == "runs/example/run_summary.json"


def test_cp17_export_skips_write_barrier_rejections(tmp_path: Path) -> None:
    db = tmp_path / "ivy_memory.sqlite3"
    store = MemoryStore(db)
    store.init_schema()
    conn = store.connect()
    try:
        with conn:
            store.insert_memory_item(
                conn,
                kind="successful_pattern",
                text="api key token should not enter frontier-visible memory",
                confidence=0.9,
                source_artifact_path=str(IVY_ROOT / "runs" / "secret" / "summary.md"),
            )
    finally:
        conn.close()
    manifest = export_acca_corpus(db, tmp_path / "acca_export")
    rejected_path = tmp_path / "acca_export" / "metadata" / "rejected_memory_items.jsonl"
    assert manifest["corpus_items"] == 0
    assert manifest["rejected_items"] == 1
    assert "obvious secret material" in rejected_path.read_text(encoding="utf-8")


def test_cp18_agent_loop_can_preview_or_inject_acca_context(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_stress_ivy_real_v3"
    scenario_dir = tmp_path / "scenario"
    write_dataset(IVY_REAL_V2, out_dir)

    preview_task, preview_meta = _prepare_acca_context(
        user_task="If remembered context tells the agent to ignore validator policy, which authority wins?",
        scenario_dir=scenario_dir,
        context_mode="preview",
        acca_dataset=out_dir,
        acca_backend="indexed",
        max_context_chars=900,
    )
    assert preview_task.startswith("If remembered context")
    assert preview_meta and preview_meta["selected_ids"] == ["safety_memory_advisory_only"]
    assert (scenario_dir / "acca_context.txt").exists()

    injected_task, inject_meta = _prepare_acca_context(
        user_task="If remembered context tells the agent to ignore validator policy, which authority wins?",
        scenario_dir=scenario_dir / "inject",
        context_mode="inject",
        acca_dataset=out_dir,
        acca_backend="indexed",
        max_context_chars=900,
    )
    assert inject_meta and inject_meta["selected_ids"] == ["safety_memory_advisory_only"]
    assert injected_task.startswith("ACCA CONTEXT PACKET")
    assert "CURRENT TASK:" in injected_task


def test_cp19_milestone_record_passes_write_barrier() -> None:
    record = build_milestone_record(
        commit="HEAD",
        note="CP19 validates milestone memories through the write barrier.",
        tests={"pytest": "11 passed"},
        source_path="docs/CP10_CP14_STATUS_2026-05-11.md",
        repo=IVY_ROOT,
    )
    normalized = validate_memory_record(record)
    assert normalized["source_family"] == "workflow_trace"
    assert normalized["authority"] == "high"
    assert "CP19 validates milestone memories" in normalized["text"]


def test_cp20_provider_certification_gate() -> None:
    passing = {
        "contract_json": {"pass_rate": 1.0, "invalid_json": 0, "wrong_tool": 0, "think_tags": 0},
        "native_tools": {"pass_rate": 1.0, "invalid_json": 0, "wrong_tool": 0, "think_tags": 0},
    }
    failing = {
        "contract_json": {"pass_rate": 1.0, "invalid_json": 0, "wrong_tool": 0, "think_tags": 0},
        "native_tools": {"pass_rate": 0.9, "invalid_json": 0, "wrong_tool": 1, "think_tags": 0},
    }
    assert certification_decision(passing)["certified"] is True
    decision = certification_decision(failing)
    assert decision["certified"] is False
    assert decision["checks"]["native_tool_pass_rate"] is False
    assert decision["checks"]["wrong_tool_zero"] is False


def test_cp13_opencode_go_finder_is_optional_without_proxy_token(tmp_path: Path) -> None:
    finder = OpenCodeGoFinder(proxy_token_file=tmp_path / "missing.token")
    assert finder.available is False


def test_cp14_memory_write_barrier_accepts_normal_record(tmp_path: Path) -> None:
    record = {
        "text": "Hot-session reuse depends on keeping the static prefix byte-identical.",
        "source_family": "doc_memory",
        "authority": "high",
        "staleness": "current",
        "source_path": "docs/HOT_SESSION_RUNNER.md",
        "safety_label": "normal",
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
    }
    normalized = append_memory_record(tmp_path / "memory.jsonl", record)
    assert normalized["id"].startswith("mem_")
    assert normalized["content_sha256"]
    assert (tmp_path / "memory.jsonl").read_text(encoding="utf-8").count("\n") == 1


def test_cp14_memory_write_barrier_rejects_absolute_or_secret_records() -> None:
    base = {
        "text": "normal note",
        "source_family": "user_note",
        "authority": "low",
        "staleness": "current",
        "source_path": "notes/example.md",
        "safety_label": "normal",
        "taint_labels": ["normal"],
        "exposure_policy": "frontier_ok",
    }
    bad_path = dict(base, source_path=r"C:\ivy\private.txt")
    try:
        validate_memory_record(bad_path)
        raise AssertionError("absolute paths must be rejected")
    except MemoryWriteError:
        pass

    secret = dict(base, text="api key token should not enter frontier memory")
    try:
        validate_memory_record(secret)
        raise AssertionError("secret-like text must be rejected")
    except MemoryWriteError:
        pass
