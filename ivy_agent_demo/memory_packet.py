from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class MemoryCandidate:
    memory_item_id: int | None
    text: str
    kind: str | None
    score: float
    source_expert: str
    source_episode_id: int | None = None
    source_artifact_path: str | None = None
    run_id: str | None = None
    provenance_present: bool = False
    source_family: str = "unknown"
    ranking: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    query: str
    task_type: str
    selected_policy: str
    selected_experts: list[str]
    selected_composers: list[str]
    top_k: int
    max_packet_chars: int
    created_at: str = field(default_factory=utc_now)


@dataclass
class PacketLine:
    text: str
    kind: str | None
    source_expert: str
    memory_item_id: int | None
    source_episode_id: int | None = None
    source_artifact_path: str | None = None
    run_id: str | None = None
    provenance_present: bool = False
    evidence_count: int = 1
    grouped_memory_item_ids: list[int] = field(default_factory=list)
    example_artifacts: list[str] = field(default_factory=list)


@dataclass
class MemoryCandidateGroup:
    group_id: str
    kind: str | None
    summary: str
    source_experts: list[str]
    candidates: list[MemoryCandidate]
    score: float
    evidence_count: int
    provenance_present: bool
    grouped_memory_item_ids: list[int]
    example_artifacts: list[str]
    example_run_ids: list[str]


@dataclass
class PacketMetrics:
    candidate_count: int
    raw_candidate_count: int
    grouped_candidate_count: int
    packet_line_count: int
    packet_chars: int
    provenance_line_rate: float
    evidence_count: int
    unique_kind_count: int
    duplicate_group_count: int
    compression_ratio: float
    chars_per_evidence: float
    latency_ms: float
    truncated: bool


@dataclass
class MemoryPacket:
    query: str
    task_type: str
    policy: str
    packet_text: str
    packet_lines: list[PacketLine]
    candidates_used: list[MemoryCandidate]
    candidates_considered: list[MemoryCandidate]
    candidate_groups: list[MemoryCandidateGroup]
    metrics: PacketMetrics
    routing_decision: RoutingDecision


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(v) for v in value]
    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}
    return value


def to_json(value: Any) -> str:
    return json.dumps(to_dict(value), indent=2, ensure_ascii=False, sort_keys=True)
