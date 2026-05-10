from __future__ import annotations

from typing import Any


class TaintExposureGate:
    """Selection and packet exposure rules for tainted memory records."""

    def __init__(self, disabled_experts: set[str]) -> None:
        self.disabled_experts = disabled_experts

    def allows_selection(self, item: Any, *, decoy_requested: bool) -> bool:
        if "safety_gate" in self.disabled_experts:
            return True
        if item.exposure_policy == "forbidden":
            return False
        if "secret_like" in item.taint_labels:
            return False
        if item.exposure_policy == "contrastive_ok" and item.authority == "decoy":
            return decoy_requested
        return True

    def rejection_reason(self, item: Any) -> tuple[str, str] | None:
        if item.exposure_policy == "forbidden" or "secret_like" in item.taint_labels:
            return "safety_taint_gate", "forbidden_exposure_policy"
        if item.exposure_policy == "metadata_only":
            return "safety_taint_gate", "metadata_only_not_selected"
        return None


class PacketCompiler:
    """Build frontier packet evidence items without leaking blocked text."""

    def evidence_item(self, item: Any) -> dict[str, Any]:
        text = item.text.replace("\n", " ")
        text_policy = "verbatim_excerpt"
        if item.exposure_policy in {"forbidden", "metadata_only"}:
            text = f"[masked by exposure_policy:{item.exposure_policy}]"
            text_policy = "masked"
        elif len(text) > 900:
            text = text[:900] + "..."
            text_policy = "truncated_excerpt"
        return {
            "id": item.id,
            "source_family": item.source_family,
            "authority": item.authority,
            "staleness": item.staleness,
            "safety_label": item.safety_label,
            "taint_labels": item.taint_labels,
            "exposure_policy": item.exposure_policy,
            "text_policy": text_policy,
            "tags": item.tags,
            "provenance": item.provenance,
            "conflicts_with": item.conflicts_with,
            "text": text,
        }
