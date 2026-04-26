import json
import re
from dataclasses import dataclass
from typing import Any

from .schemas import TOOL_SCHEMAS


@dataclass
class ValidationResult:
    ok: bool
    kind: str
    tool: str | None
    arguments: dict[str, Any] | None
    final: str | None
    failure_taxonomy: list[str]
    details: dict[str, Any]


def _has_markdown_fence(text: str) -> bool:
    return "```" in text


def _has_think_tags(text: str) -> bool:
    return bool(re.search(r"</?think>", text, flags=re.IGNORECASE))


def _type_ok(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    return True


def _path_is_unsafe(path_value: str) -> bool:
    normalized = path_value.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    if len(path_value) >= 2 and path_value[1] == ":":
        return True
    if ".." in normalized.split("/"):
        return True
    return False


def validate_model_output(raw_text: str) -> ValidationResult:
    text = raw_text.strip()
    failures: list[str] = []
    details: dict[str, Any] = {}

    if _has_markdown_fence(text):
        failures.append("markdown_fence")
    if _has_think_tags(text):
        failures.append("think_tags")

    try:
        payload = json.loads(text)
        details["parse"] = "ok"
    except Exception as exc:
        details["parse"] = "error"
        details["parse_error"] = str(exc)
        failures.append("invalid_json")
        return ValidationResult(
            ok=False,
            kind="invalid",
            tool=None,
            arguments=None,
            final=None,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    if not isinstance(payload, dict):
        failures.append("json_not_object")
        return ValidationResult(
            ok=False,
            kind="invalid",
            tool=None,
            arguments=None,
            final=None,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    keys = set(payload.keys())
    if keys == {"final"}:
        final_value = payload.get("final")
        if not isinstance(final_value, str):
            failures.append("final_not_string")
            return ValidationResult(
                ok=False,
                kind="invalid",
                tool=None,
                arguments=None,
                final=None,
                failure_taxonomy=sorted(set(failures)),
                details=details,
            )
        return ValidationResult(
            ok=(len(failures) == 0),
            kind="final",
            tool=None,
            arguments=None,
            final=final_value,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    if keys != {"tool", "arguments"}:
        failures.append("extra_or_missing_top_fields")
        return ValidationResult(
            ok=False,
            kind="invalid",
            tool=None,
            arguments=None,
            final=None,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    tool = payload.get("tool")
    arguments = payload.get("arguments")

    if not isinstance(tool, str):
        failures.append("tool_not_string")
    if not isinstance(arguments, dict):
        failures.append("arguments_not_object")

    if failures:
        return ValidationResult(
            ok=False,
            kind="invalid",
            tool=tool if isinstance(tool, str) else None,
            arguments=arguments if isinstance(arguments, dict) else None,
            final=None,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    if tool not in TOOL_SCHEMAS:
        failures.append("unknown_tool")
        return ValidationResult(
            ok=False,
            kind="invalid",
            tool=tool,
            arguments=arguments,
            final=None,
            failure_taxonomy=sorted(set(failures)),
            details=details,
        )

    schema = TOOL_SCHEMAS[tool]
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    allowed_fields = set(props.keys())

    missing = sorted(required - set(arguments.keys()))
    if missing:
        failures.extend([f"missing_required_field:{name}" for name in missing])

    extra_fields = sorted(set(arguments.keys()) - allowed_fields)
    if extra_fields and not schema.get("additional_properties", False):
        failures.extend([f"extra_argument_field:{name}" for name in extra_fields])

    for field_name, field_schema in props.items():
        if field_name not in arguments:
            continue
        expected_type = field_schema.get("type")
        if expected_type and not _type_ok(arguments[field_name], expected_type):
            failures.append(f"wrong_type:{field_name}")
            continue
        enum_values = field_schema.get("enum")
        if enum_values is not None and arguments[field_name] not in enum_values:
            failures.append(f"invalid_enum:{field_name}")

    for field_name, value in arguments.items():
        if field_name == "path" and isinstance(value, str):
            if _path_is_unsafe(value):
                failures.append("unsafe_path")

    return ValidationResult(
        ok=(len(failures) == 0),
        kind="tool" if len(failures) == 0 else "invalid",
        tool=tool,
        arguments=arguments,
        final=None,
        failure_taxonomy=sorted(set(failures)),
        details=details,
    )
