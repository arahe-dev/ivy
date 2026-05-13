from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    script = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cp93_cp95_adapter_lifecycle(tmp_path: Path) -> None:
    module = load_script("run_agent_memory_adapter.py")
    report = tmp_path / "adapter.md"

    result = module.run_adapter(tmp_path / "store", report, reset=True)

    assert result["ok"] is True
    assert result["before_task_selected"] >= 1
    assert result["before_edit_selected"] >= 1
    assert result["after_test_delta_count"] == 1
    assert result["after_task_delta_count"] == 1
    assert "before_task" in report.read_text(encoding="utf-8")


def test_cp96_cp98_answer_ab_prefers_packet_memory(tmp_path: Path) -> None:
    module = load_script("run_agent_memory_answer_ab.py")
    report = tmp_path / "answer_ab.md"

    result = module.run_answer_ab(tmp_path / "store", report, reset=True)

    assert result["ok"] is True
    assert result["no_memory_quality"] == 0.0
    assert result["with_memory_quality"] == 1.0
    assert result["seeded_delta_count"] == 3
    assert "packet-v2 memory" in report.read_text(encoding="utf-8")


def test_cp100_long_session_drill_distills_to_deltas(tmp_path: Path) -> None:
    module = load_script("run_agent_memory_long_session_drill.py")
    report = tmp_path / "long.md"

    result = module.run_long_session_drill(tmp_path / "store", report, records=120, target_tokens=10_000, reset=True)

    assert result["ok"] is True
    assert result["records"] == 120
    assert result["delta_count"] == 3
    assert result["selected_count"] >= 1
    assert result["projected_shards_for_target"] >= 1
    assert "Long-Session Drill" in report.read_text(encoding="utf-8")
