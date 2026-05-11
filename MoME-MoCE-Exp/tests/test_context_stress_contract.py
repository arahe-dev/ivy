from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.mome_moce_harness import MoMEMoCERouter, evaluate_case, load_cases, load_corpus
from scripts.validate_context_stress_dataset import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_generated_datasets_validate_against_strict_contracts() -> None:
    for scale in ("smoke", "medium", "stress"):
        errors, warnings, summary = validate_dataset(ROOT / "out" / f"context_stress_{scale}")
        assert errors == []
        assert summary["cases"] == 62
        assert summary["items"] > 0
        # Dropped template refs may be recorded as warnings, but generated corpus refs must be clean.
        assert all("dangling" not in warning for warning in warnings)


def test_smoke_harness_preserves_recall_and_emits_schema_valid_proofs() -> None:
    route_validator = Draft202012Validator(load_schema("route_proof.schema.json"))
    packet_validator = Draft202012Validator(load_schema("frontier_context_packet.schema.json"))
    items = load_corpus(ROOT / "out" / "context_stress_smoke")
    cases = load_cases(ROOT / "out" / "context_stress_smoke")
    router = MoMEMoCERouter(items)

    passed = 0
    for case in cases:
        result = router.route(case["query"])
        evaluated = evaluate_case(case, result)
        passed += int(evaluated["passed"])
        assert list(route_validator.iter_errors(result.route_proof)) == []
        assert list(packet_validator.iter_errors(result.frontier_packet)) == []
        assert isinstance(result.frontier_packet, dict)
        assert result.frontier_packet["packet_version"] == "acca.frontier_context_packet.v0.1"
        assert result.frontier_packet["packet_mode"] in {
            "compact_default",
            "proof_lite",
            "contradiction_aware",
            "abstain_notice",
        }
        assert result.route_proof["proof_version"] == "acca.route_proof.v0.1"
    assert passed == 62


def test_route_proofs_expose_real_expert_outputs() -> None:
    items = load_corpus(ROOT / "out" / "context_stress_smoke")
    cases = {case["id"]: case for case in load_cases(ROOT / "out" / "context_stress_smoke")}
    router = MoMEMoCERouter(items)
    result = router.route(cases["bench_001"]["query"])
    proof = result.route_proof

    assert "sparse_lexical_memory" in {output["expert"] for output in proof["expert_outputs"]}
    assert proof["activated_experts"]
    assert proof["selected_evidence"]
    assert proof["authority_chain"]
    assert proof["tokens_avoided"] > proof["frontier_packet_tokens"]
