from __future__ import annotations

import enum
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GGUFValueType(enum.IntEnum):
    UINT8 = 0
    INT8 = 1
    UINT16 = 2
    INT16 = 3
    UINT32 = 4
    INT32 = 5
    FLOAT32 = 6
    BOOL = 7
    STRING = 8
    ARRAY = 9
    UINT64 = 10
    INT64 = 11
    FLOAT64 = 12


TYPE_SIZES = {
    GGUFValueType.UINT8: 1,
    GGUFValueType.INT8: 1,
    GGUFValueType.UINT16: 2,
    GGUFValueType.INT16: 2,
    GGUFValueType.UINT32: 4,
    GGUFValueType.INT32: 4,
    GGUFValueType.FLOAT32: 4,
    GGUFValueType.BOOL: 1,
    GGUFValueType.UINT64: 8,
    GGUFValueType.INT64: 8,
    GGUFValueType.FLOAT64: 8,
}


GGML_TYPE_BLOCKS = {
    0: (4, 1),  # F32
    1: (2, 1),  # F16
    2: (20, 32), 3: (24, 32), 6: (22, 32), 7: (26, 32),
    8: (34, 32), 9: (36, 32), 10: (40, 32), 11: (44, 32),
    12: (2, 1), 13: (1, 1), 14: (1, 1), 15: (2, 1),
    16: (2, 1), 17: (4, 1), 18: (56, 256), 19: (64, 256),
    20: (84, 256), 21: (92, 256), 22: (52, 256), 23: (56, 256),
    24: (1, 1), 25: (2, 1), 26: (4, 1), 27: (2, 1),
    28: (210, 256), 29: (216, 256), 30: (8, 32), 31: (12, 32),
    32: (16, 32), 33: (10, 32), 34: (12, 32), 35: (12, 32),
    36: (16, 32), 37: (16, 32), 38: (8, 32), 39: (10, 32),
}


@dataclass
class TensorInfo:
    name: str
    dims: list[int]
    type_id: int
    offset: int
    estimated_bytes: int | None
    category: str


class GGUFReader:
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("rb")

    def close(self) -> None:
        self.file.close()

    def read(self, n: int) -> bytes:
        data = self.file.read(n)
        if len(data) != n:
            raise EOFError("unexpected end of GGUF")
        return data

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.read(8))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self.read(8))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def f64(self) -> float:
        return struct.unpack("<d", self.read(8))[0]

    def string(self) -> str:
        length = self.u64()
        return self.read(length).decode("utf-8", errors="replace")

    def value(self, value_type: int) -> Any:
        typ = GGUFValueType(value_type)
        if typ == GGUFValueType.UINT8:
            return self.read(1)[0]
        if typ == GGUFValueType.INT8:
            return struct.unpack("<b", self.read(1))[0]
        if typ == GGUFValueType.UINT16:
            return struct.unpack("<H", self.read(2))[0]
        if typ == GGUFValueType.INT16:
            return struct.unpack("<h", self.read(2))[0]
        if typ == GGUFValueType.UINT32:
            return self.u32()
        if typ == GGUFValueType.INT32:
            return self.i32()
        if typ == GGUFValueType.FLOAT32:
            return self.f32()
        if typ == GGUFValueType.BOOL:
            return bool(self.read(1)[0])
        if typ == GGUFValueType.STRING:
            return self.string()
        if typ == GGUFValueType.UINT64:
            return self.u64()
        if typ == GGUFValueType.INT64:
            return self.i64()
        if typ == GGUFValueType.FLOAT64:
            return self.f64()
        if typ == GGUFValueType.ARRAY:
            elem_type = self.u32()
            count = self.u64()
            if count > 100_000:
                self._skip_array(elem_type, count)
                return {"skipped_array_type": elem_type, "count": count}
            return [self.value(elem_type) for _ in range(count)]
        raise ValueError(f"unsupported GGUF value type {value_type}")

    def _skip_array(self, elem_type: int, count: int) -> None:
        typ = GGUFValueType(elem_type)
        size = TYPE_SIZES.get(typ)
        if size is not None:
            self.file.seek(size * count, 1)
            return
        for _ in range(count):
            self.value(elem_type)


def inspect_gguf(path: Path, max_tensors: int = 20000) -> dict[str, Any]:
    warnings: list[str] = []
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "metadata": {},
        "summary": {},
        "tensor_categories": {},
        "tensors": [],
        "warnings": warnings,
    }
    if not path.exists():
        warnings.append("model file does not exist")
        return info
    reader = GGUFReader(path)
    try:
        magic = reader.read(4)
        if magic != b"GGUF":
            warnings.append(f"not a GGUF file; magic={magic!r}")
            return info
        version = reader.u32()
        tensor_count = reader.u64()
        kv_count = reader.u64()
        info["version"] = version
        info["tensor_count"] = tensor_count
        info["metadata_kv_count"] = kv_count

        metadata: dict[str, Any] = {}
        for _ in range(kv_count):
            key = reader.string()
            value_type = reader.u32()
            metadata[key] = reader.value(value_type)
        info["metadata"] = metadata
        info["summary"] = summarize_metadata(metadata)

        tensors: list[TensorInfo] = []
        for index in range(min(tensor_count, max_tensors)):
            name = reader.string()
            n_dims = reader.u32()
            dims = [reader.u64() for _ in range(n_dims)]
            type_id = reader.u32()
            offset = reader.u64()
            tensors.append(
                TensorInfo(
                    name=name,
                    dims=dims,
                    type_id=type_id,
                    offset=offset,
                    estimated_bytes=estimate_tensor_bytes(dims, type_id),
                    category=categorize_tensor(name),
                )
            )
        if tensor_count > max_tensors:
            warnings.append(f"tensor list truncated to {max_tensors} of {tensor_count}")
        info["tensors"] = [tensor.__dict__ for tensor in tensors]
        info["tensor_categories"] = aggregate_tensors(tensors)
    except Exception as exc:
        warnings.append(f"GGUF parse failed: {exc}")
    finally:
        reader.close()
    return info


def summarize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    arch = metadata.get("general.architecture")
    prefix = f"{arch}." if arch else ""
    keys = {
        "architecture": "general.architecture",
        "model_name": "general.name",
        "block_count": f"{prefix}block_count",
        "context_length": f"{prefix}context_length",
        "expert_count": f"{prefix}expert_count",
        "expert_used_count": f"{prefix}expert_used_count",
    }
    return {name: metadata.get(key) for name, key in keys.items() if metadata.get(key) is not None}


def estimate_tensor_bytes(dims: list[int], type_id: int) -> int | None:
    block = GGML_TYPE_BLOCKS.get(type_id)
    if not block:
        return None
    type_size, block_size = block
    elements = 1
    for dim in dims:
        elements *= dim
    blocks = (elements + block_size - 1) // block_size
    return blocks * type_size


def categorize_tensor(name: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ["attn", "q_proj", "k_proj", "v_proj", "o_proj", ".wq", ".wk", ".wv", ".wo"]):
        return "attention"
    if any(token in lower for token in ["router", "gate", "ffn_gate", "gate_inp"]):
        return "router/gate"
    if any(token in lower for token in ["expert", "experts", "ffn_exps", "moe", "exps"]):
        return "expert/ffn_exps/MoE"
    if any(token in lower for token in ["ffn", "feed_forward", "up_proj", "down_proj"]):
        return "dense FFN"
    if "norm" in lower or "ln_" in lower:
        return "norm"
    if any(token in lower for token in ["embed", "token_embd", "output", "lm_head"]):
        return "embedding/output"
    return "unknown"


def aggregate_tensors(tensors: list[TensorInfo]) -> dict[str, Any]:
    categories: dict[str, dict[str, Any]] = {}
    for tensor in tensors:
        item = categories.setdefault(tensor.category, {"count": 0, "estimated_bytes": 0, "unknown_bytes": 0})
        item["count"] += 1
        if tensor.estimated_bytes is None:
            item["unknown_bytes"] += 1
        else:
            item["estimated_bytes"] += tensor.estimated_bytes
    return categories
