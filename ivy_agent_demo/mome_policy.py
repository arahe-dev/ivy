from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MOME_POLICY_DIR = Path(__file__).resolve().parent / "mome_policies"


REQUIRED_POLICY_FIELDS = {
    "name",
    "description",
    "task_types_supported",
    "experts_enabled",
    "expert_weights",
    "source_family_weights",
    "exact_match_weights",
    "max_candidates_per_expert",
    "max_total_candidates",
    "max_packet_chars",
    "require_provenance",
    "group_duplicates",
    "caution_rules",
    "injection_allowed",
    "recommended_use",
}


@dataclass
class MomePolicy:
    name: str
    document: dict[str, Any]
    path: Path


def list_mome_policies(policy_dir: Path | None = None) -> list[str]:
    root = policy_dir or MOME_POLICY_DIR
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("mome_*.json"))


def load_mome_policy(name: str | None, policy_dir: Path | None = None) -> MomePolicy:
    policy_name = name or "mome_auto"
    if not policy_name.startswith("mome_"):
        policy_name = f"mome_{policy_name}"
    root = policy_dir or MOME_POLICY_DIR
    path = root / f"{policy_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"MoME policy not found: {path}")
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    validate_mome_policy(document, path)
    return MomePolicy(name=str(document["name"]), document=document, path=path)


def validate_mome_policy(document: dict[str, Any], path: Path | None = None) -> None:
    missing = sorted(REQUIRED_POLICY_FIELDS - set(document))
    if missing:
        label = str(path) if path else str(document.get("name", "<unknown>"))
        raise ValueError(f"MoME policy missing required fields in {label}: {missing}")
    if not str(document["name"]).startswith("mome_"):
        raise ValueError(f"MoME policy name must start with mome_: {document['name']}")
    for key in ("experts_enabled", "task_types_supported", "caution_rules"):
        if not isinstance(document.get(key), list):
            raise ValueError(f"MoME policy field must be a list: {key}")
    for key in ("expert_weights", "source_family_weights", "exact_match_weights"):
        if not isinstance(document.get(key), dict):
            raise ValueError(f"MoME policy field must be an object: {key}")
    for key in ("max_candidates_per_expert", "max_total_candidates", "max_packet_chars"):
        if int(document.get(key, 0)) < 0:
            raise ValueError(f"MoME policy numeric field must be non-negative: {key}")


def policy_packet_options(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "enable_grouping": bool(policy.get("group_duplicates", True)),
    "max_evidence_per_group": int(policy.get("max_evidence_per_group") or 3),
    "max_groups_per_kind": int(policy.get("max_groups_per_kind") or 3),
    "min_distinct_kinds": int(policy.get("min_distinct_kinds") or 1),
}
