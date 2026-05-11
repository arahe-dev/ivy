from __future__ import annotations

import json
from pathlib import Path

from scripts.run_answer_level_eval import run_eval
from scripts.generate_ivy_real_v3_dataset import write_dataset
from scripts.memory_write_barrier import MemoryWriteError, append_memory_record, validate_memory_record
from scripts.run_latency_gate import run_latency_gate
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
