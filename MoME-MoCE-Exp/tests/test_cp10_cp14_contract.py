from __future__ import annotations

import json
from pathlib import Path

from scripts.run_answer_level_eval import run_eval
from scripts.generate_ivy_real_v3_dataset import write_dataset
from scripts.mome_moce_harness import MoMEMoCERouter, benchmark, load_cases, load_corpus


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
