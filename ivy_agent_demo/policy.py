from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PolicyDecision:
    approved: bool
    failure_taxonomy: list[str]
    normalized_arguments: dict[str, Any]
    notes: dict[str, Any]


class PolicyGate:
    def __init__(self, sandbox_root: Path) -> None:
        self.sandbox_root = sandbox_root.resolve()
        self.sandbox_out = (self.sandbox_root / "out").resolve()

    @staticmethod
    def _looks_like_network(text: str) -> bool:
        return bool(re.search(r"https?://|ftp://|\\\\", text, flags=re.IGNORECASE))

    @staticmethod
    def _looks_like_delete_intent(text: str) -> bool:
        patterns = [
            r"\bdelete\b",
            r"\bremove\b",
            r"\brm\b",
            r"\bdel\b",
            r"\bformat\b",
            r"\bwipe\b",
        ]
        return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

    def _resolve_under(self, rel_path: str, root: Path) -> Path | None:
        candidate = Path(rel_path)
        if candidate.is_absolute():
            return None
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return None
        return resolved

    def evaluate(self, tool: str, arguments: dict[str, Any]) -> PolicyDecision:
        failures: list[str] = []
        notes: dict[str, Any] = {}
        normalized = dict(arguments)

        if tool != "ask_user":
            for value in arguments.values():
                if isinstance(value, str):
                    if self._looks_like_network(value):
                        failures.append("network_not_allowed")
                    if self._looks_like_delete_intent(value):
                        failures.append("delete_intent_not_allowed")

        if tool in {"fs_list", "fs_read"}:
            path_value = arguments.get("path", "")
            if not isinstance(path_value, str):
                failures.append("path_not_string")
            else:
                resolved = self._resolve_under(path_value, self.sandbox_root)
                if resolved is None:
                    failures.append("path_outside_sandbox")
                else:
                    normalized["path"] = str(resolved)
                    notes["resolved_path"] = str(resolved)

        if tool == "fs_write":
            path_value = arguments.get("path", "")
            if not isinstance(path_value, str):
                failures.append("path_not_string")
            else:
                resolved = self._resolve_under(path_value, self.sandbox_root)
                if resolved is None:
                    failures.append("path_outside_sandbox")
                else:
                    try:
                        resolved.relative_to(self.sandbox_out)
                    except ValueError:
                        failures.append("write_outside_sandbox_out")
                    normalized["path"] = str(resolved)
                    notes["resolved_path"] = str(resolved)

            mode = arguments.get("mode")
            if mode not in {"overwrite", "append"}:
                failures.append("invalid_write_mode")

        if tool == "calc_eval":
            expr = arguments.get("expr", "")
            if not isinstance(expr, str):
                failures.append("expr_not_string")
            else:
                if not re.fullmatch(r"[0-9\s+\-*/%().]+", expr):
                    failures.append("unsafe_calc_expression")

        if tool == "ask_user":
            question = arguments.get("question", "")
            if not isinstance(question, str) or not question.strip():
                failures.append("invalid_question")

        return PolicyDecision(
            approved=(len(set(failures)) == 0),
            failure_taxonomy=sorted(set(failures)),
            normalized_arguments=normalized,
            notes=notes,
        )
