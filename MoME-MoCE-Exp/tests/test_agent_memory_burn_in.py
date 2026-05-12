from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_agent_memory_burn_in.py"


def load_burn_in_module():
    spec = importlib.util.spec_from_file_location("agent_memory_burn_in", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_memory_burn_in_roundtrip(tmp_path: Path) -> None:
    module = load_burn_in_module()
    report = tmp_path / "burn_in.md"

    result = module.run_burn_in(tmp_path / "store", report, reset=True)

    assert result["ok"] is True
    assert result["initial_delta_count"] >= 4
    assert result["after_test_delta_count"] >= 1
    assert result["before_task_selected"] >= 1
    assert result["packet_v2_selected"] >= 1
    assert report.exists()
    assert "context_packet v0.2" in report.read_text(encoding="utf-8")
