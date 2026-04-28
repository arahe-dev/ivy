from __future__ import annotations

import re
import time

from .memory_packet import MemoryCandidate, MemoryPacket, PacketLine, PacketMetrics, RoutingDecision


def _short(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def _evidence(candidate: MemoryCandidate) -> str:
    if candidate.source_artifact_path or candidate.run_id:
        parts = []
        if candidate.run_id:
            parts.append(f"run {candidate.run_id}")
        if candidate.source_artifact_path:
            parts.append(f"artifact {candidate.source_artifact_path}")
        return " Evidence: " + "; ".join(parts) + "."
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


def compose_packet(
    query: str,
    decision: RoutingDecision,
    candidates: list[MemoryCandidate],
    latency_ms: float = 0.0,
) -> MemoryPacket:
    start = time.perf_counter()
    used: list[MemoryCandidate] = []
    lines: list[PacketLine] = []
    text_lines = ["Relevant memory packet:"]

    for candidate in candidates:
        body = f"- {line_prefix(decision.task_type, candidate)}: {_short(candidate.text)}{_evidence(candidate)}"
        tentative = "\n".join(text_lines + [body])
        if len(tentative) > decision.max_packet_chars:
            break
        text_lines.append(body)
        used.append(candidate)
        lines.append(
            PacketLine(
                text=body,
                kind=candidate.kind,
                source_expert=candidate.source_expert,
                memory_item_id=candidate.memory_item_id,
                source_episode_id=candidate.source_episode_id,
                source_artifact_path=candidate.source_artifact_path,
                run_id=candidate.run_id,
                provenance_present=candidate.provenance_present,
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
    truncated = len(used) < len(candidates)
    provenance_rate = round(sum(1 for line in lines if line.provenance_present) / len(lines), 4) if lines else 0.0
    metrics = PacketMetrics(
        candidate_count=len(candidates),
        packet_line_count=len(lines),
        packet_chars=len(packet_text),
        provenance_line_rate=provenance_rate,
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
        metrics=metrics,
        routing_decision=decision,
    )
