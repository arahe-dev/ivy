from __future__ import annotations

from typing import Any


VALID_STRATEGIES = {"d-acca", "helper-lazy"}
BLOCKED_EXPOSURE_POLICIES = {"forbidden"}
BLOCKED_SAFETY_LABELS = {"secret_like", "unsafe_decoy"}


class ContractError(ValueError):
    def __init__(self, message: str, *, path: str = "$") -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


def validate_bundle(snapshot: dict[str, Any], packet_response: dict[str, Any], proof_response: dict[str, Any] | None = None) -> None:
    issues = collect_contract_issues(snapshot, packet_response, proof_response)
    if issues["errors"]:
        raise ContractError("; ".join(issues["errors"]))


def collect_contract_issues(
    snapshot: dict[str, Any] | None,
    packet_response: dict[str, Any] | None,
    proof_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for label, func, value in (
        ("snapshot", validate_snapshot, snapshot),
        ("packet", validate_packet_response, packet_response),
    ):
        try:
            func(value)
        except ContractError as exc:
            errors.append(f"{label} {exc}")

    if packet_response and proof_response:
        try:
            validate_packet_proof_match(packet_response, proof_response)
        except ContractError as exc:
            errors.append(f"proof {exc}")

    if packet_response:
        for evidence in packet_response.get("packet", {}).get("evidence", []) or []:
            if not isinstance(evidence, dict):
                continue
            item_id = str(evidence.get("id") or "<unknown>")
            exposure = str(evidence.get("exposure_policy") or "")
            safety = str(evidence.get("safety_label") or "")
            staleness = str(evidence.get("staleness") or "")
            if exposure in BLOCKED_EXPOSURE_POLICIES:
                errors.append(f"packet evidence {item_id} exposes blocked policy {exposure}")
            if safety in BLOCKED_SAFETY_LABELS:
                errors.append(f"packet evidence {item_id} exposes blocked safety label {safety}")
            if staleness and staleness not in {"current", "unknown"}:
                warnings.append(f"packet evidence {item_id} is {staleness}")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_snapshot(snapshot: dict[str, Any] | None) -> None:
    require_mapping(snapshot, "$")
    health = require_mapping(snapshot.get("health"), "$.health")
    hooks = require_mapping(snapshot.get("hooks"), "$.hooks")
    memories = require_mapping(snapshot.get("memories"), "$.memories")
    if health.get("ok") is not True:
        raise ContractError("health.ok must be true", path="$.health.ok")
    require_string(health.get("service_version"), "$.health.service_version")
    require_int(health.get("memory_count"), "$.health.memory_count", minimum=0)
    require_string(hooks.get("service_version"), "$.hooks.service_version")
    require_list(hooks.get("endpoints"), "$.hooks.endpoints")
    require_int(memories.get("total"), "$.memories.total", minimum=0)
    items = require_list(memories.get("items"), "$.memories.items")
    if len(items) > memories["total"]:
        raise ContractError("items cannot exceed total", path="$.memories.items")


def validate_packet_response(response: dict[str, Any] | None) -> None:
    require_mapping(response, "$")
    route_id = require_string(response.get("route_id"), "$.route_id")
    strategy = require_string(response.get("strategy"), "$.strategy")
    if strategy not in VALID_STRATEGIES:
        raise ContractError(f"strategy must be one of {sorted(VALID_STRATEGIES)}", path="$.strategy")
    require_string(response.get("decision"), "$.decision")
    require_number(response.get("confidence"), "$.confidence", minimum=0, maximum=100)
    require_number(response.get("latency_ms"), "$.latency_ms", minimum=0)
    selected_ids = require_string_list(response.get("selected_ids"), "$.selected_ids")
    packet = require_mapping(response.get("packet"), "$.packet")
    require_string(packet.get("packet_version"), "$.packet.packet_version")
    require_string(packet.get("role"), "$.packet.role")
    require_string(packet.get("query"), "$.packet.query")
    evidence = require_list(packet.get("evidence"), "$.packet.evidence")
    evidence_ids = [require_string(item.get("id") if isinstance(item, dict) else None, f"$.packet.evidence[{index}].id") for index, item in enumerate(evidence)]
    if evidence_ids != selected_ids:
        raise ContractError(f"selected_ids {selected_ids!r} do not match packet evidence ids {evidence_ids!r}", path="$.selected_ids")
    packet_route_id = packet.get("route_id") or packet.get("case_id")
    if packet_route_id and packet_route_id != route_id:
        raise ContractError(f"packet route id {packet_route_id!r} does not match wrapper route id {route_id!r}", path="$.packet.route_id")
    budget = require_mapping(packet.get("context_budget"), "$.packet.context_budget")
    selected_count = budget.get("selected_evidence_items")
    if selected_count is not None and int(selected_count) != len(selected_ids):
        raise ContractError("context_budget selected count mismatch", path="$.packet.context_budget.selected_evidence_items")
    artifact_errors = response.get("artifact_errors") or []
    if artifact_errors:
        raise ContractError(f"engine returned artifact errors: {artifact_errors}", path="$.artifact_errors")


def validate_packet_proof_match(packet_response: dict[str, Any], proof_response: dict[str, Any]) -> None:
    require_mapping(proof_response, "$")
    packet_route_id = require_string(packet_response.get("route_id"), "$.route_id")
    proof_route_id = proof_response.get("route_id")
    proof = extract_route_proof(proof_response)
    if proof_route_id and proof_route_id != packet_route_id:
        raise ContractError(f"stored route id {proof_route_id!r} does not match packet route id {packet_route_id!r}", path="$.route_id")
    route_proof_id = proof.get("route_id") or proof.get("case_id")
    if route_proof_id and route_proof_id != packet_route_id:
        raise ContractError(f"route proof id {route_proof_id!r} does not match packet route id {packet_route_id!r}", path="$.route_proof.route_id")
    proof_selected = selected_ids_from_proof(proof)
    packet_selected = require_string_list(packet_response.get("selected_ids"), "$.selected_ids")
    if proof_selected != packet_selected:
        raise ContractError(f"proof selected ids {proof_selected!r} do not match packet selected ids {packet_selected!r}", path="$.route_proof.selected_ids")


def extract_route_proof(proof_response: dict[str, Any]) -> dict[str, Any]:
    proof = proof_response.get("route_proof", proof_response)
    return require_mapping(proof, "$.route_proof")


def selected_ids_from_proof(proof: dict[str, Any]) -> list[str]:
    if isinstance(proof.get("selected_ids"), list):
        return [str(value) for value in proof["selected_ids"]]
    selected_evidence = proof.get("selected_evidence")
    if isinstance(selected_evidence, list):
        return [str(item.get("id")) for item in selected_evidence if isinstance(item, dict) and item.get("id")]
    return []


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("expected object", path=path)
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError("expected list", path=path)
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("expected non-empty string", path=path)
    return value


def require_string_list(value: Any, path: str) -> list[str]:
    items = require_list(value, path)
    return [require_string(item, f"{path}[{index}]") for index, item in enumerate(items)]


def require_int(value: Any, path: str, *, minimum: int | None = None) -> int:
    if not isinstance(value, int):
        raise ContractError("expected int", path=path)
    if minimum is not None and value < minimum:
        raise ContractError(f"expected >= {minimum}", path=path)
    return value


def require_number(value: Any, path: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if not isinstance(value, (int, float)):
        raise ContractError("expected number", path=path)
    number = float(value)
    if minimum is not None and number < minimum:
        raise ContractError(f"expected >= {minimum}", path=path)
    if maximum is not None and number > maximum:
        raise ContractError(f"expected <= {maximum}", path=path)
    return number
