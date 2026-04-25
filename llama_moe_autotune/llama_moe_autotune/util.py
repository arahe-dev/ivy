from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=json_default), encoding="utf-8")


def sanitize_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("_") or "run"


def quote_cmd_arg(arg: str) -> str:
    if not arg:
        return '""'
    if re.search(r'[\s"&|<>^()]', arg):
        return '"' + arg.replace('"', r'\"') + '"'
    return arg


def command_to_string(command: list[str]) -> str:
    return " ".join(quote_cmd_arg(str(part)) for part in command)


def bytes_to_gib(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024**3), 3)
