from __future__ import annotations

from pathlib import Path
from typing import Any

from .ranking import best_result, rank_results, safest_result
from .util import command_to_string, write_json


def write_all_reports(
    out_latest: Path,
    system_info: dict[str, Any],
    model_info: dict[str, Any],
    supported_flags: dict[str, Any],
    candidates: list[dict[str, Any]],
    results: list[dict[str, Any]],
    dry_run: bool,
    reasoning_behavior: dict[str, Any] | None = None,
) -> None:
    out_latest.mkdir(parents=True, exist_ok=True)
    write_json(out_latest / "system_info.json", system_info)
    write_json(out_latest / "model_info.json", model_info)
    write_json(out_latest / "supported_flags.json", supported_flags)
    write_json(out_latest / "candidates.json", candidates)
    write_json(out_latest / "results.json", results)

    ranked = rank_results([dict(item) for item in results]) if results else []
    write_ranked_markdown(
        out_latest / "ranked_results.md",
        system_info,
        model_info,
        supported_flags,
        candidates,
        ranked,
        dry_run,
        reasoning_behavior,
    )
    write_override_plans(out_latest / "override_plans.md", model_info, supported_flags)

    best = best_result(results)
    safe = safest_result(results)
    write_json(out_latest / "best_config.json", best or {})
    write_launch_bat(out_latest / "launch_best.bat", best, reasoning_behavior)
    write_launch_bat(out_latest / "launch_safe.bat", safe, reasoning_behavior)


def write_ranked_markdown(
    path: Path,
    system_info: dict[str, Any],
    model_info: dict[str, Any],
    supported_flags: dict[str, Any],
    candidates: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    dry_run: bool,
    reasoning_behavior: dict[str, Any] | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# llama.cpp MoE Autotune Results")
    lines.append("")
    lines.append(f"Mode: {'dry run' if dry_run else 'benchmark'}")
    if reasoning_behavior:
        disabled = reasoning_behavior.get("disable_reasoning", False)
        supported = reasoning_behavior.get("supported", False)
        status = "disabled" if disabled else "enabled"
        if disabled and supported:
            lines.append(f"Reasoning: {status} (--reasoning-budget 0 injected)")
        elif disabled and not supported:
            lines.append(f"Reasoning: {status} (flag requested but not supported)")
        else:
            lines.append(f"Reasoning: {status}")
    else:
        lines.append("Reasoning: unknown")
    lines.append("")
    lines.append("## Machine summary")
    os_info = system_info.get("os", {})
    lines.append(f"- OS: {os_info.get('platform') or os_info}")
    lines.append(f"- CPU: {system_info.get('cpu', {}).get('name') or 'unknown'}")
    memory = system_info.get("memory", {})
    lines.append(f"- RAM total bytes: {memory.get('total_bytes', 'unknown')}")
    nvidia = system_info.get("nvidia", {})
    if nvidia.get("available"):
        for idx, gpu in enumerate(nvidia.get("gpus", [])):
            lines.append(
                f"- GPU {idx}: {gpu.get('name')} total={gpu.get('memory_total_mib')} MiB free={gpu.get('memory_free_mib')} MiB"
            )
    else:
        lines.append("- NVIDIA GPU: unavailable")
    lines.append("")
    lines.append("## Model summary")
    summary = model_info.get("summary", {})
    lines.append(f"- Path: {model_info.get('path')}")
    lines.append(f"- Size bytes: {model_info.get('size_bytes')}")
    lines.append(f"- Architecture: {summary.get('architecture', 'unknown')}")
    lines.append(f"- Name: {summary.get('model_name', 'unknown')}")
    lines.append(f"- Layers/block count: {summary.get('block_count', 'unknown')}")
    lines.append(f"- Context length: {summary.get('context_length', 'unknown')}")
    lines.append(f"- Experts: {summary.get('expert_count', 'unknown')}")
    lines.append(f"- Experts used: {summary.get('expert_used_count', 'unknown')}")
    lines.append("")
    lines.append("## Supported flags")
    supported = supported_flags.get("supported", {})
    for flag, value in sorted(supported.items()):
        lines.append(f"- `{flag}`: {value}")
    unsupported = supported_flags.get("unsupported", [])
    if unsupported:
        lines.append(
            f"- Unsupported recorded: {', '.join(f'`{flag}`' for flag in unsupported)}"
        )
    lines.append("")
    lines.append("## Tested candidates")
    lines.append(f"- Candidate count generated: {len(candidates)}")
    if dry_run:
        lines.append("- No benchmark commands were executed.")
    else:
        lines.append(f"- Candidate count executed: {len(ranked)}")
    lines.append("")

    if ranked:
        lines.append("## Top 5 configs")
        for result in ranked[:5]:
            cand = result.get("candidate", {})
            lines.append(
                f"- Rank {result.get('rank')}: candidate {cand.get('index')} `{cand.get('name')}` "
                f"outcome={result.get('outcome')} decode_tps={result.get('decode_tps')} "
                f"wall_s={result.get('wall_seconds')} score={result.get('score')}"
            )
        lines.append("")
        best = next((item for item in ranked if item.get("outcome") == "success"), None)
        if best:
            lines.append("## Best config")
            lines.append(
                f"- Candidate: {best.get('candidate', {}).get('index')} `{best.get('candidate', {}).get('name')}`"
            )
            lines.append(
                f"- Decode tok/s: {best.get('decode_tps')} estimated={best.get('decode_tps_estimated')}"
            )
            lines.append(f"- Command: `{best.get('command_string')}`")
            lines.append("")
        safe = safest_result(ranked)
        if safe:
            lines.append("## Safest config")
            lines.append(
                f"- Candidate: {safe.get('candidate', {}).get('index')} `{safe.get('candidate', {}).get('name')}`"
            )
            lines.append(f"- Command: `{safe.get('command_string')}`")
            lines.append("")
        lines.append("## Failed configs summary")
        counts: dict[str, int] = {}
        for result in ranked:
            outcome = result.get("outcome")
            if outcome != "success":
                counts[outcome] = counts.get(outcome, 0) + 1
        if counts:
            for outcome, count in sorted(counts.items()):
                lines.append(f"- {outcome}: {count}")
        else:
            lines.append("- No failed configs recorded.")
        lines.append("")
    else:
        lines.append("## Candidate command preview")
        for candidate in candidates[:10]:
            lines.append(
                f"- Candidate {candidate.get('index')}: `{candidate.get('command_string', candidate.get('name'))}`"
            )
        lines.append("")

    lines.append("## Interpretation")
    if dry_run:
        lines.append(
            "- Dry run completed candidate planning and environment inspection only."
        )
    else:
        lines.append(
            "- Prefer the best config only if it is stable across repeated short prompts."
        )
        lines.append(
            "- Treat estimated decode rates as lower confidence than parsed llama.cpp timings."
        )
    lines.append("")
    lines.append("## Next recommended experiments")
    lines.append(
        "- Re-run the top 2 configs with a longer but still bounded prompt set."
    )
    lines.append(
        "- If GPU memory warnings appear, reduce `-ngl`, context, batch, or KV precision before increasing scope."
    )
    lines.append(
        "- Consider tensor override experiments only after tensor categories are identified with confidence."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_launch_bat(
    path: Path,
    result: dict[str, Any] | None,
    reasoning_behavior: dict[str, Any] | None = None,
) -> None:
    if not result:
        path.write_text(
            "@echo off\necho No successful config available yet.\nexit /b 1\n",
            encoding="utf-8",
        )
        return
    command = command_to_string([str(item) for item in result.get("command", [])])
    reasoning_note = ""
    if (
        reasoning_behavior
        and reasoning_behavior.get("disable_reasoning")
        and reasoning_behavior.get("supported")
    ):
        reasoning_note = "\nREM Reasoning disabled: --reasoning-budget 0"
    path.write_text(f"@echo off\n{reasoning_note}\n{command}\n", encoding="utf-8")


def write_override_plans(
    path: Path, model_info: dict[str, Any], supported_flags: dict[str, Any]
) -> None:
    lines = ["# Tensor Override Plans", ""]
    if not supported_flags.get("supported", {}).get("--override-tensor"):
        lines.append(
            "`--override-tensor` is not supported by this llama.cpp binary, so no override candidates were generated."
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    tensors = model_info.get("tensors", [])
    if not tensors:
        lines.append(
            "No tensor list was available, so no override candidates were generated."
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    categories: dict[str, list[str]] = {}
    for tensor in tensors:
        categories.setdefault(tensor.get("category", "unknown"), []).append(
            tensor.get("name", "")
        )
    lines.append("Potential placement intent, not enabled by default:")
    lines.append("- Attention/shared tensors: CUDA if memory permits")
    lines.append("- Router/gate tensors: CUDA if names are identifiable")
    lines.append("- MoE expert tensors: CPU by default for huge models")
    lines.append("- Embedding/output tensors: only move when memory margin is clear")
    lines.append("")
    for category in [
        "attention",
        "router/gate",
        "expert/ffn_exps/MoE",
        "embedding/output",
    ]:
        names = [name for name in categories.get(category, []) if name][:20]
        lines.append(f"## {category}")
        if names:
            for name in names:
                lines.append(f"- `{name}`")
        else:
            lines.append("- No confident tensor names found.")
        lines.append("")
    lines.append(
        "No automatic override command is emitted because llama.cpp tensor placement syntax and model tensor naming should be verified manually first."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
