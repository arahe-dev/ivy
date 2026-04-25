from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .flags import is_supported


@dataclass
class Candidate:
    index: int
    name: str
    context: int
    batch: int
    ubatch: int
    n_predict: int
    ngl: str | int
    kv: str
    mmap: bool
    direct_io: bool
    cpu_moe: bool
    n_cpu_moe: int | None = None
    fit: bool = False
    extra_args: list[str] = field(default_factory=list)
    reasoning_disabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "context": self.context,
            "batch": self.batch,
            "ubatch": self.ubatch,
            "n_predict": self.n_predict,
            "ngl": self.ngl,
            "kv": self.kv,
            "mmap": self.mmap,
            "direct_io": self.direct_io,
            "cpu_moe": self.cpu_moe,
            "n_cpu_moe": self.n_cpu_moe,
            "fit": self.fit,
            "extra_args": self.extra_args,
            "reasoning_disabled": self.reasoning_disabled,
        }


def build_candidate_command(
    candidate: Candidate,
    llama_cli: Path,
    model: Path,
    prompt: str,
    supported_flags: dict[str, Any],
    seed: int = 12345,
    disable_reasoning: bool = False,
) -> list[str]:
    command = [
        str(llama_cli),
        "-m",
        str(model),
        "-p",
        prompt,
        "-n",
        str(candidate.n_predict),
    ]
    command.extend(["-c", str(candidate.context), "-b", str(candidate.batch)])
    if is_supported(supported_flags, "-ub"):
        command.extend(["-ub", str(candidate.ubatch)])
    if is_supported(supported_flags, "--seed"):
        command.extend(["--seed", str(seed)])
    if is_supported(supported_flags, "-ngl"):
        command.extend(["-ngl", str(candidate.ngl)])
    if candidate.mmap and is_supported(supported_flags, "--mmap"):
        command.append("--mmap")
    if candidate.direct_io and is_supported(supported_flags, "--direct-io"):
        command.append("--direct-io")
    if candidate.cpu_moe and is_supported(supported_flags, "--cpu-moe"):
        command.append("--cpu-moe")
    if candidate.n_cpu_moe is not None and is_supported(supported_flags, "--n-cpu-moe"):
        command.extend(["--n-cpu-moe", str(candidate.n_cpu_moe)])
    if candidate.fit and is_supported(supported_flags, "--fit"):
        command.append("--fit")
    if candidate.kv == "q8_0":
        if is_supported(supported_flags, "-ctk"):
            command.extend(["-ctk", "q8_0"])
        if is_supported(supported_flags, "-ctv"):
            command.extend(["-ctv", "q8_0"])
    elif candidate.kv == "q4_0":
        if is_supported(supported_flags, "-ctk"):
            command.extend(["-ctk", "q4_0"])
        if is_supported(supported_flags, "-ctv"):
            command.extend(["-ctv", "q4_0"])
    if disable_reasoning and is_supported(supported_flags, "--reasoning-budget"):
        command.extend(["--reasoning-budget", "0"])
    if is_supported(supported_flags, "--single-turn"):
        command.append("--single-turn")
    if is_supported(supported_flags, "--no-display-prompt"):
        command.append("--no-display-prompt")
    command.extend(candidate.extra_args)
    return command


def generate_candidates(
    supported_flags: dict[str, Any],
    model_info: dict[str, Any],
    max_candidates: int,
    n_predict: int = 32,
    experiment: str = "default",
    disable_reasoning: bool = False,
) -> list[Candidate]:
    if experiment == "post_reasoning_tune":
        return _generate_post_reasoning_candidates(
            supported_flags, model_info, max_candidates, n_predict, disable_reasoning
        )
    return _generate_default_candidates(
        supported_flags, model_info, max_candidates, n_predict, disable_reasoning
    )


def _generate_post_reasoning_candidates(
    supported_flags: dict[str, Any],
    model_info: dict[str, Any],
    max_candidates: int,
    n_predict: int,
    disable_reasoning: bool,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    def add(
        name: str,
        context: int,
        batch: int,
        ubatch: int,
        ngl: str | int,
        kv: str,
        cpu_moe: bool,
        direct_io: bool = False,
        n_cpu_moe: int | None = None,
        pred: int | None = None,
        fit: bool = False,
    ) -> None:
        if len(candidates) >= max_candidates:
            return
        candidates.append(
            Candidate(
                index=len(candidates),
                name=name,
                context=context,
                batch=batch,
                ubatch=ubatch,
                n_predict=pred if pred is not None else n_predict,
                ngl=ngl,
                kv=kv,
                mmap=True,
                direct_io=direct_io,
                cpu_moe=cpu_moe,
                n_cpu_moe=n_cpu_moe,
                fit=fit,
                reasoning_disabled=disable_reasoning,
            )
        )

    ngls: list[str | int] = [0, 4, 8, 12, 16]
    if is_supported(supported_flags, "-ngl"):
        ngl_values = supported_flags.get("n_gpu_layers_values", {})
        if ngl_values.get("auto"):
            ngls.append("auto")

    n_cpu_moes = [8, 16, 24, 32]
    kv_types = ["q4_0", "q8_0"]
    contexts = [512, 1024]

    for ngl in ngls:
        for n_cpu_moe in n_cpu_moes:
            for kv in kv_types:
                for ctx in contexts:
                    add(
                        f"prt_ngl{ngl}_cpu{n_cpu_moe}_kv{kv}_ctx{ctx}",
                        ctx,
                        32,
                        16,
                        ngl,
                        kv,
                        True,
                        n_cpu_moe=n_cpu_moe,
                    )

    if not candidates:
        add("prt_baseline", 512, 32, 16, 0, "q4_0", True)

    return candidates[:max_candidates]


def _generate_default_candidates(
    supported_flags: dict[str, Any],
    model_info: dict[str, Any],
    max_candidates: int,
    n_predict: int,
    disable_reasoning: bool,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    def add(
        name: str,
        context: int,
        batch: int,
        ubatch: int,
        ngl: str | int,
        kv: str,
        cpu_moe: bool,
        direct_io: bool = False,
        n_cpu_moe: int | None = None,
        pred: int | None = None,
        fit: bool = False,
    ) -> None:
        if len(candidates) >= max_candidates:
            return
        candidates.append(
            Candidate(
                index=len(candidates),
                name=name,
                context=context,
                batch=batch,
                ubatch=ubatch,
                n_predict=pred if pred is not None else n_predict,
                ngl=ngl,
                kv=kv,
                mmap=True,
                direct_io=direct_io,
                cpu_moe=cpu_moe,
                n_cpu_moe=n_cpu_moe,
                fit=fit,
                reasoning_disabled=disable_reasoning,
            )
        )

    block_count = _int_or_none(model_info.get("summary", {}).get("block_count"))
    moe_values = _moe_values(block_count)

    add("survival_smoke", 512, 32, 16, 0, "q4_0", True, pred=16)

    contexts = [512, 1024, 2048]
    batches = [32, 64, 128, 256]
    ubatches = [16, 32, 64, 128]
    kvs = ["default", "q8_0", "q4_0"]
    ngls: list[str | int] = [0]
    if is_supported(supported_flags, "-ngl"):
        ngl_values = supported_flags.get("n_gpu_layers_values", {})
        if ngl_values.get("auto"):
            ngls.append("auto")
        if ngl_values.get("all"):
            ngls.append("all")
        ngls.extend([8, 16, 24, 32])
        if block_count:
            ngls.extend(
                sorted(
                    {max(1, block_count // 4), max(1, block_count // 2), block_count}
                )
            )

    for context in contexts:
        for ngl in ngls:
            for kv in kvs:
                batch = _pick_batch(context, batches)
                ubatch = _pick_ubatch(batch, ubatches)
                add(
                    f"ctx{context}_ngl{ngl}_kv{kv}",
                    context,
                    batch,
                    ubatch,
                    ngl,
                    kv,
                    True,
                )

    for n_cpu_moe in moe_values:
        add(
            f"cpu_moe_{n_cpu_moe}_ctx1024_ngl8",
            1024,
            64,
            32,
            8,
            "q8_0",
            True,
            n_cpu_moe=n_cpu_moe,
        )

    if is_supported(supported_flags, "--direct-io"):
        add("direct_io_safe", 512, 32, 16, 0, "q4_0", True, direct_io=True)

    return candidates[:max_candidates]


def _pick_batch(context: int, batches: list[int]) -> int:
    if context <= 512:
        return 64
    if context <= 1024:
        return 128
    return min(256, max(batches))


def _pick_ubatch(batch: int, ubatches: list[int]) -> int:
    return max(value for value in ubatches if value <= batch)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _moe_values(block_count: int | None) -> list[int]:
    values = {8, 16, 24, 32}
    if block_count:
        values.update(
            {
                max(1, block_count // 8),
                max(1, block_count // 4),
                max(1, block_count // 2),
            }
        )
    return sorted(values)
