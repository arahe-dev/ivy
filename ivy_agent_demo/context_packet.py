from __future__ import annotations

import string
import re
import time

from .memory_packet import MemoryCandidate, MemoryCandidateGroup, MemoryPacket, PacketLine, PacketMetrics, RoutingDecision


def _short(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def normalize_for_grouping(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[a-z]:\\[^\s]+", " ", text)
    text = re.sub(r"/[^\s]+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation.replace("<", "").replace(">", "").replace("_", "")))
    text = re.sub(r"\b20\d{6}_\d{6}(?:_\d+)?\b", " ", text)
    text = re.sub(r"\b\d+\.\d+\b", "<num>", text)
    return re.sub(r"\s+", " ", text).strip()


def token_overlap(a: str, b: str) -> float:
    ta = set(normalize_for_grouping(a).split())
    tb = set(normalize_for_grouping(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _evidence(group: MemoryCandidateGroup) -> str:
    if group.provenance_present:
        latest = group.candidates[0]
        parts = []
        if latest.run_id:
            parts.append(f"latest run {latest.run_id}")
        if latest.source_artifact_path:
            parts.append(f"artifact {latest.source_artifact_path}")
        prefix = f" Evidence: {group.evidence_count} supporting memor"
        prefix += "y" if group.evidence_count == 1 else "ies"
        if parts:
            prefix += "; " + "; ".join(parts)
        if group.example_artifacts:
            prefix += "; examples " + ", ".join(group.example_artifacts[:3])
        return prefix + "."
    return " Evidence: missing provenance; treat as retrieval hint only."


def line_prefix(task_type: str, candidate: MemoryCandidate) -> str:
    if task_type == "benchmark":
        return "Benchmark memory"
    if task_type == "safety":
        return "Safety memory"
    if task_type == "workflow":
        return "Workflow memory"
    if task_type == "tool_debug":
        if candidate.kind and "warning" in candidate.kind:
            return "Prior validation/debug warning"
        return "Validation debug memory"
    if task_type == "planning":
        return "Planning memory"
    return "Relevant memory"


def canonical_kind(kind: str | None) -> str:
    if not kind:
        return "unknown"
    mapping = {
        "json_contamination_warning": "json_contamination_warning",
        "benchmark_result": "benchmark_result",
        "policy_warning": "policy_warning",
        "validation_warning": "validation_failure",
        "failure_warning": "validation_failure",
        "successful_pattern": "workflow_success",
    }
    return mapping.get(kind, kind)


def group_summary(kind: str | None, text: str, count: int) -> str:
    ck = canonical_kind(kind)
    lower = text.lower()
    if ck == "json_contamination_warning":
        return "Qwen benchmark responses emitted <think> tags before or inside generated text, creating JSON validation risk."
    if ck == "benchmark_result" and "ctx=512" in lower:
        return _short(text, 180)
    if ck in {"policy_warning", "safety_warning"}:
        return _short(text, 180)
    if ck == "validation_failure":
        return _short(text, 180)
    if ck == "workflow_success":
        return _short(text, 180)
    if count > 1:
        return _short(text, 180)
    return _short(text, 220)


def group_candidates(candidates: list[MemoryCandidate], enable_grouping: bool = True, max_evidence_per_group: int = 3) -> list[MemoryCandidateGroup]:
    groups: list[MemoryCandidateGroup] = []
    for candidate in sorted(candidates, key=lambda c: c.score, reverse=True):
        candidate_norm = normalize_for_grouping(candidate.text)
        if not enable_grouping:
            matched = None
        else:
            matched = None
            ck = canonical_kind(candidate.kind)
            for group in groups:
                if canonical_kind(group.kind) != ck:
                    continue
                group_norm = group.group_id.split(":", 2)[-1]
                if group_norm == candidate_norm or token_overlap(group.candidates[0].text, candidate.text) >= 0.72:
                    matched = group
                    break
        if matched is None:
            group_id = f"{canonical_kind(candidate.kind)}:{len(groups) + 1}:{candidate_norm}"
            matched = MemoryCandidateGroup(
                group_id=group_id,
                kind=candidate.kind,
                summary=candidate.text,
                source_experts=[],
                candidates=[],
                score=0.0,
                evidence_count=0,
                provenance_present=False,
                grouped_memory_item_ids=[],
                example_artifacts=[],
                example_run_ids=[],
            )
            groups.append(matched)
        matched.candidates.append(candidate)
        matched.source_experts = sorted(set(matched.source_experts + [candidate.source_expert]))
        matched.score = max(matched.score, candidate.score)
        matched.evidence_count = len(matched.candidates)
        matched.provenance_present = matched.provenance_present or candidate.provenance_present
        if candidate.memory_item_id is not None and candidate.memory_item_id not in matched.grouped_memory_item_ids:
            matched.grouped_memory_item_ids.append(candidate.memory_item_id)
        if candidate.source_artifact_path and candidate.source_artifact_path not in matched.example_artifacts:
            matched.example_artifacts.append(candidate.source_artifact_path)
        if candidate.run_id and candidate.run_id not in matched.example_run_ids:
            matched.example_run_ids.append(candidate.run_id)
        matched.summary = group_summary(candidate.kind, matched.candidates[0].text, len(matched.candidates))
    return sorted(groups, key=lambda g: (g.score, g.evidence_count, g.provenance_present), reverse=True)


def apply_diversity(groups: list[MemoryCandidateGroup], policy: dict | None) -> list[MemoryCandidateGroup]:
    if not policy:
        return groups
    max_per_kind = int(policy.get("max_groups_per_kind") or len(groups) or 1)
    counts: dict[str, int] = {}
    selected = []
    for group in groups:
        kind = canonical_kind(group.kind)
        if counts.get(kind, 0) >= max_per_kind:
            continue
        counts[kind] = counts.get(kind, 0) + 1
        selected.append(group)
    return selected


def compose_packet(
    query: str,
    decision: RoutingDecision,
    candidates: list[MemoryCandidate],
    latency_ms: float = 0.0,
    policy: dict | None = None,
) -> MemoryPacket:
    start = time.perf_counter()
    used: list[MemoryCandidate] = []
    lines: list[PacketLine] = []
    text_lines = ["Relevant memory packet:"]
    enable_grouping = bool((policy or {}).get("enable_grouping", True))
    max_evidence = int((policy or {}).get("max_evidence_per_group") or 3)
    groups = apply_diversity(group_candidates(candidates, enable_grouping, max_evidence), policy)

    for group in groups:
        representative = group.candidates[0]
        prefix = line_prefix(decision.task_type, representative)
        if group.evidence_count > 1 and decision.task_type == "tool_debug":
            prefix = "Repeated validation/debug warning"
        body = f"- {prefix}: {_short(group.summary)}{_evidence(group)}"
        tentative = "\n".join(text_lines + [body])
        if len(tentative) > decision.max_packet_chars:
            break
        text_lines.append(body)
        used.extend(group.candidates)
        lines.append(
            PacketLine(
                text=body,
                kind=group.kind,
                source_expert=",".join(group.source_experts),
                memory_item_id=representative.memory_item_id,
                source_episode_id=representative.source_episode_id,
                source_artifact_path=representative.source_artifact_path,
                run_id=representative.run_id,
                provenance_present=group.provenance_present,
                evidence_count=group.evidence_count,
                grouped_memory_item_ids=group.grouped_memory_item_ids,
                example_artifacts=group.example_artifacts[:max_evidence],
            )
        )

    if decision.task_type == "benchmark" and len("\n".join(text_lines)) + 90 <= decision.max_packet_chars:
        text_lines.append("Caution: single-run TPS is smoke data, not a stable performance claim.")
    if decision.task_type == "tool_debug" and len("\n".join(text_lines)) + 100 <= decision.max_packet_chars:
        text_lines.append("Suggested bias: treat think/reasoning tags before JSON as a validation risk.")
    if decision.task_type == "safety" and len("\n".join(text_lines)) + 110 <= decision.max_packet_chars:
        text_lines.append("Safety bias: prefer sandbox-relative paths; absolute paths may trigger policy rejection.")
    if decision.task_type == "workflow" and len("\n".join(text_lines)) + 80 <= decision.max_packet_chars:
        text_lines.append("Workflow bias: prefer successful calc/write procedure evidence when present.")
    if not used and "none" not in decision.selected_experts:
        text_lines.append("- No matching memory candidates were selected. Treat this packet as empty.")
    elif "none" in decision.selected_experts:
        text_lines.append("- No memory selected by policy. Baseline packet only.")

    packet_text = "\n".join(text_lines)
    included_ids = {c.memory_item_id for c in used if c.memory_item_id is not None}
    truncated = len(included_ids) < len({c.memory_item_id for c in candidates if c.memory_item_id is not None})
    provenance_rate = round(sum(1 for line in lines if line.provenance_present) / len(lines), 4) if lines else 0.0
    evidence_count = sum(line.evidence_count for line in lines)
    raw_count = len(candidates)
    grouped_count = len(groups)
    compression_ratio = round((len(lines) / raw_count), 4) if raw_count else 0.0
    chars_per_evidence = round((len(packet_text) / max(evidence_count, 1)), 3)
    metrics = PacketMetrics(
        candidate_count=len(candidates),
        raw_candidate_count=raw_count,
        grouped_candidate_count=grouped_count,
        packet_line_count=len(lines),
        packet_chars=len(packet_text),
        provenance_line_rate=provenance_rate,
        evidence_count=evidence_count,
        unique_kind_count=len({canonical_kind(line.kind) for line in lines}),
        duplicate_group_count=sum(1 for line in lines if line.evidence_count > 1),
        compression_ratio=compression_ratio,
        chars_per_evidence=chars_per_evidence,
        latency_ms=round(latency_ms + ((time.perf_counter() - start) * 1000.0), 3),
        truncated=truncated,
    )
    return MemoryPacket(
        query=query,
        task_type=decision.task_type,
        policy=decision.selected_policy,
        packet_text=packet_text,
        packet_lines=lines,
        candidates_used=used,
        candidates_considered=candidates,
        candidate_groups=groups,
        metrics=metrics,
        routing_decision=decision,
    )
