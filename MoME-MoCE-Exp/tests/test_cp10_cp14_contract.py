from __future__ import annotations

import json
from pathlib import Path

from scripts.run_answer_level_eval import run_eval


ROOT = Path(__file__).resolve().parents[1]
IVY_REAL_V2 = ROOT / "out" / "context_stress_ivy_real_v2"


def test_cp10_answer_level_eval_prefers_d_acca() -> None:
    payload = run_eval(IVY_REAL_V2, backend="indexed", naive_top_k=5, limit=24)
    summary = payload["summary"]
    assert summary["d_acca"]["quality"] >= 0.9
    assert summary["d_acca"]["quality"] >= summary["naive_bm25"]["quality"]
    assert summary["d_acca"]["quality"] > summary["no_context"]["quality"]
