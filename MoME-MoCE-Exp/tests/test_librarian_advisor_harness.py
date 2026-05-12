from __future__ import annotations

import json

from scripts.run_librarian_advisor_harness import (
    ModelAdvisorConfig,
    extract_json_object,
    extract_response_text,
    main,
    model_opencode_go_advice,
    parse_model_librarian_payload,
)
from scripts.generate_blackbox_packet_cases import main as generate_blackbox_cases_main
from scripts.run_blackbox_packet_eval import main as blackbox_eval_main
from scripts.run_real_replay_packet_eval import main as real_replay_eval_main


def test_librarian_advisor_harness_smoke(tmp_path) -> None:
    out_dir = tmp_path / "librarian"
    rc = main(
        [
            "--cases",
            "eval/librarian_harness_cases.json",
            "--strategy",
            "fixture",
            "--candidate-backend",
            "indexed",
            "--limit",
            "3",
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    summary_path = out_dir / "librarian_harness_summary.json"
    results_path = out_dir / "librarian_harness_results.json"
    report_path = out_dir / "librarian_harness_report.md"
    assert summary_path.exists()
    assert results_path.exists()
    assert report_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    assert summary["cases"] == 3
    assert "direct_quality" in summary
    assert "librarian_quality" in summary
    assert results["runner_version"] == "d_acca.librarian_advisor_harness.v0.1"
    assert all(row["advice"]["queries"] for row in results["results"])
    assert all("direct_score" in row and "librarian_score" in row for row in results["results"])


def test_dd_rule_distills_model_help_into_fast_deterministic_path(tmp_path) -> None:
    out_dir = tmp_path / "dd_rule"
    rc = main(
        [
            "--cases",
            "eval/librarian_harness_cases.json",
            "--strategy",
            "dd-rule",
            "--candidate-backend",
            "indexed",
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    summary = json.loads((out_dir / "librarian_harness_summary.json").read_text(encoding="utf-8"))
    assert summary["cases"] == 5
    assert summary["librarian_quality"] == 1.0
    assert summary["librarian_harmed_cases"] == []
    assert summary["forbidden_hits"]["librarian"] == 0
    assert set(summary["librarian_helped_cases"]) == {
        "lib_cp27_recall_price_vague",
        "lib_v2_hot_cache_footgun",
    }


def test_spec_dd_verifies_multi_head_draft_with_d_acca(tmp_path) -> None:
    out_dir = tmp_path / "spec_dd"
    rc = main(
        [
            "--cases",
            "eval/librarian_harness_cases.json",
            "--strategy",
            "spec-dd",
            "--candidate-backend",
            "indexed",
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    summary = json.loads((out_dir / "librarian_harness_summary.json").read_text(encoding="utf-8"))
    results = json.loads((out_dir / "librarian_harness_results.json").read_text(encoding="utf-8"))
    assert summary["librarian_quality"] == 1.0
    assert summary["forbidden_hits"]["librarian"] == 0
    assert summary["librarian_harmed_cases"] == []
    assert all(row["advice"]["strategy"].startswith("spec-dd") for row in results["results"])
    assert any("Draft heads:" in track for row in results["results"] for track in row["advice"]["side_tracks"])


def test_spec_dd_lazy_defers_verification_to_final_route(tmp_path) -> None:
    out_dir = tmp_path / "spec_dd_lazy"
    rc = main(
        [
            "--cases",
            "eval/librarian_harness_cases.json",
            "--strategy",
            "spec-dd-lazy",
            "--candidate-backend",
            "indexed",
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    summary = json.loads((out_dir / "librarian_harness_summary.json").read_text(encoding="utf-8"))
    results = json.loads((out_dir / "librarian_harness_results.json").read_text(encoding="utf-8"))
    assert summary["librarian_quality"] == 1.0
    assert summary["forbidden_hits"]["librarian"] == 0
    assert summary["librarian_harmed_cases"] == []
    assert all(row["advice"]["strategy"] == "spec-dd-lazy" for row in results["results"])
    assert any("final D-ACCA bundle route" in track for row in results["results"] for track in row["advice"]["side_tracks"])


def test_helper_lazy_and_blackbox_packet_eval(tmp_path) -> None:
    dataset = tmp_path / "blackbox_dataset"
    cases = tmp_path / "blackbox_cases.json"
    out_dir = tmp_path / "blackbox_eval"
    rc = generate_blackbox_cases_main(
        [
            "--count",
            "60",
            "--edge-ratio",
            "0.3",
            "--seed",
            "99",
            "--dataset",
            str(dataset),
            "--cases-out",
            str(cases),
        ]
    )
    assert rc == 0

    rc = blackbox_eval_main(
        [
            "--cases",
            str(cases),
            "--variants",
            "d-acca",
            "helper-lazy",
            "bm25",
            "--candidate-backend",
            "indexed",
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    summary = json.loads((out_dir / "blackbox_packet_eval_summary.json").read_text(encoding="utf-8"))
    assert set(summary) == {"d-acca", "helper-lazy", "bm25"}
    assert summary["helper-lazy"]["cases"] == 60
    assert summary["helper-lazy"]["quality"] >= summary["d-acca"]["quality"]
    assert summary["helper-lazy"]["forbidden_hits"] <= summary["bm25"]["forbidden_hits"]


def test_real_replay_packet_eval_from_codex_style_jsonl(tmp_path) -> None:
    sessions_root = tmp_path / "sessions"
    session_dir = sessions_root / "2026" / "05" / "12"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "rollout-test.jsonl"
    events = [
        {
            "timestamp": "2026-05-12T12:00:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "what have we actually made here, a search engine or acca context memory engine?"}],
            },
        },
        {
            "timestamp": "2026-05-12T12:01:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "how do we use the librarian and confidence gate without making DeepSeek the hot path?"}],
            },
        },
        {
            "timestamp": "2026-05-12T12:02:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "can Signal ping the phone and Recall Board become the visual second brain?"}],
            },
        },
    ]
    session_file.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    out_dir = tmp_path / "real_replay_eval"
    rc = real_replay_eval_main(
        [
            "--sessions-root",
            str(sessions_root),
            "--count",
            "30",
            "--seed",
            "7",
            "--dataset",
            str(tmp_path / "real_replay_dataset"),
            "--cases",
            str(tmp_path / "real_replay_cases.json"),
            "--out",
            str(out_dir),
            "--variants",
            "helper-lazy",
            "dd-rule",
            "--candidate-backend",
            "indexed",
        ]
    )
    assert rc == 0
    summary = json.loads((out_dir / "real_replay_packet_eval_summary.json").read_text(encoding="utf-8"))
    results = json.loads((out_dir / "real_replay_packet_eval_results.json").read_text(encoding="utf-8"))
    report = (out_dir / "real_replay_packet_eval_report.md").read_text(encoding="utf-8")
    assert set(summary) == {"helper-lazy", "dd-rule"}
    assert summary["helper-lazy"]["cases"] == 30
    assert results["runner_version"] == "d_acca.real_replay_packet_eval.v0.1"
    assert results["replay_generation"]["matched_user_turns"] == 3
    assert "Fixed variation bank" in report


def test_model_librarian_response_parsing() -> None:
    response = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": """```json
{
  "escalation_mode": "blocking_escalation",
  "intent_summary": "Freshness-sensitive Recall pricing lookup.",
  "queries": ["current Recall Cloud production pricing", "authoritative Recall Cloud price"],
  "entity_terms": ["Recall"],
  "negative_constraints": ["Reject stale price drafts."],
  "side_tracks": ["Check whether no current price exists."],
  "rationale": "The user asked for current production pricing."
}
```""",
                    }
                ],
            }
        ]
    }
    case = {"id": "pricing", "query": "latest Recall Cloud production price"}
    text = extract_response_text(response)
    payload = extract_json_object(text)
    advice = parse_model_librarian_payload(payload, case, 12.3456, "model-opencode-go:deepseek-v4-flash")

    assert advice.escalation_mode == "blocking_escalation"
    assert advice.entity_terms == ["recall"]
    assert advice.queries[:1] == ["current Recall Cloud production pricing"]
    assert advice.latency_ms == 12.346


def test_model_librarian_falls_back_to_rule(monkeypatch) -> None:
    def fail_call(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr("scripts.run_librarian_advisor_harness.call_opencode_go_responses", fail_call)
    advice = model_opencode_go_advice(
        {"id": "pricing", "query": "latest Recall Cloud production price"},
        ModelAdvisorConfig(timeout_seconds=0.01, fallback="rule"),
    )

    assert advice.strategy.endswith(":fallback_rule")
    assert advice.escalation_mode == "blocking_escalation"
    assert "deterministic rule librarian" in advice.rationale


def test_model_librarian_guardrails_drop_negative_queries_and_normalize_entities() -> None:
    payload = {
        "escalation_mode": "parallel_advisory",
        "intent_summary": "Sandbox permissions lookup.",
        "queries": [
            "demo agent write permissions sandbox_workspace out directory",
            "sandbox write permissions not stale draft",
        ],
        "entity_terms": ["phase 1 agent", "agent tools", "sandbox_workspace"],
        "negative_constraints": ["Reject stale write-anywhere notes."],
        "side_tracks": [],
        "rationale": "Safety policy lookup.",
    }
    case = {"id": "sandbox", "query": "Can the demo agent poke around or write wherever?"}

    advice = parse_model_librarian_payload(payload, case, 1.0, "model-opencode-go:deepseek-v4-flash")

    assert advice.queries == ["demo agent write permissions sandbox_workspace out directory"]
    assert advice.entity_terms == ["sandbox"]
    assert advice.escalation_mode == "blocking_escalation"
