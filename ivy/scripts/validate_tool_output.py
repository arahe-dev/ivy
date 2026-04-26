#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def load_text(path_or_text, is_file):
    if is_file:
        return Path(path_or_text).read_text(encoding="utf-8-sig")
    return path_or_text


def strip_code_fence(text):
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    if fence:
        return fence.group(1), True
    return text, False


def find_balanced_json(text):
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def try_json(text):
    try:
        return json.loads(text), None
    except Exception as exc:
        return None, str(exc)


def jsonish_equal_text(text, parsed):
    compact_a = re.sub(r"\s+", "", text)
    compact_b = re.sub(r"\s+", "", json.dumps(parsed, ensure_ascii=False, separators=(",", ":")))
    # Also allow the original formatting if json.loads accepted it and no non-JSON
    # wrapper text exists. This function is used after strict parsing only.
    return compact_a == compact_b or text.strip().startswith("{") and text.strip().endswith("}")


def type_ok(value, expected):
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True


def validate_schema(obj, schema):
    failures = []
    parsed_tool = None
    parsed_args = None

    if not isinstance(obj, dict):
        return False, ["json_not_object"], None, None

    allowed_top = set(schema.get("allowed_top_fields", ["tool", "arguments"]))
    invented_top = sorted(set(obj.keys()) - allowed_top)
    if invented_top and not schema.get("allow_extra_top_fields", False):
        failures.append("invented_top_fields:" + ",".join(invented_top))

    expected_tool = schema.get("expected_tool")
    forbidden_tools = set(schema.get("forbidden_tools") or [])
    allowed_tools = set(schema.get("allowed_tools") or [])

    if "tool" in obj:
        parsed_tool = obj.get("tool")
    elif "name" in obj:
        parsed_tool = obj.get("name")
        failures.append("wrong_tool_field_name")
    else:
        failures.append("missing_tool")

    if parsed_tool in forbidden_tools:
        failures.append("forbidden_tool:" + str(parsed_tool))
    if allowed_tools and parsed_tool not in allowed_tools:
        failures.append("tool_not_allowed:" + str(parsed_tool))
    if expected_tool and parsed_tool != expected_tool:
        failures.append(f"wrong_tool:{parsed_tool}")

    if "arguments" in obj:
        parsed_args = obj.get("arguments")
    elif any(k not in ("tool", "name") for k in obj.keys()):
        parsed_args = {k: v for k, v in obj.items() if k not in ("tool", "name")}
        failures.append("arguments_not_nested")
    else:
        failures.append("missing_arguments")
        parsed_args = None

    if not isinstance(parsed_args, dict):
        failures.append("arguments_not_object")
        parsed_args = {} if parsed_args is None else parsed_args

    arg_schema = schema.get("argument_schema") or {}
    required = schema.get("required_arguments") or list(arg_schema.keys())
    for key in required:
        if key not in parsed_args:
            failures.append("missing_required_argument:" + key)

    allow_extra_args = schema.get("allow_extra_arguments", False)
    extra_args = sorted(set(parsed_args.keys()) - set(arg_schema.keys()))
    if extra_args and not allow_extra_args:
        failures.append("invented_argument_fields:" + ",".join(extra_args))

    for key, spec in arg_schema.items():
        if key not in parsed_args:
            continue
        if isinstance(spec, str):
            expected_type = spec
            enum = None
        else:
            expected_type = spec.get("type")
            enum = spec.get("enum")
        if expected_type and not type_ok(parsed_args[key], expected_type):
            failures.append(f"wrong_argument_type:{key}")
        if enum is not None and parsed_args[key] not in enum:
            failures.append(f"invalid_enum:{key}")

    return len(failures) == 0, failures, parsed_tool, parsed_args


def validate(raw, schema):
    stripped = raw.strip()
    has_think = bool(re.search(r"</?think>", raw, re.IGNORECASE))
    fenced_text, has_fence = strip_code_fence(stripped)
    extra_prose = False
    clean_source = None
    raw_json, raw_error = try_json(stripped)
    raw_parse_success = raw_json is not None

    parsed = None
    parse_mode = "none"
    if raw_parse_success:
        parsed = raw_json
        parse_mode = "raw"
        clean_source = stripped
    else:
        candidate = fenced_text if has_fence else find_balanced_json(stripped)
        if candidate and candidate != stripped:
            extra_prose = True
        if candidate:
            clean_json, clean_error = try_json(candidate.strip())
            if clean_json is not None:
                parsed = clean_json
                parse_mode = "cleaned"
                clean_source = candidate.strip()

    if raw_parse_success:
        before_after = stripped
        # If strict JSON parsing succeeded, there is no wrapper prose by definition.
        extra_prose = False
    elif clean_source:
        extra_prose = stripped != clean_source and not has_fence

    schema_ok = False
    schema_failures = []
    parsed_tool = None
    parsed_args = None
    if parsed is not None:
        schema_ok, schema_failures, parsed_tool, parsed_args = validate_schema(parsed, schema)

    failures = []
    if has_think:
        failures.append("think_tags")
    if has_fence:
        failures.append("markdown_fence")
    if extra_prose:
        failures.append("extra_prose")
    if parsed is None:
        failures.append("json_missing_or_invalid")
    failures.extend(schema_failures)

    raw_strict = raw_parse_success and schema_ok and not has_think and not has_fence and not extra_prose
    cleaned_pass = parse_mode == "cleaned" and schema_ok and not has_think

    if raw_strict:
        status = "pass"
        retry = False
    elif cleaned_pass:
        status = "partial"
        retry = False
    elif parsed is not None and not schema_ok:
        status = "fail"
        retry = True
    else:
        status = "fail"
        retry = True

    return {
        "status": status,
        "failure_taxonomy": sorted(set(failures)),
        "retry_recommended": retry,
        "raw_parse_success": raw_parse_success,
        "parse_mode": parse_mode,
        "schema_pass": schema_ok,
        "parsed_tool": parsed_tool,
        "parsed_arguments": parsed_args,
        "parsed_json": parsed,
        "has_think_tags": has_think,
        "has_markdown_fence": has_fence,
        "has_extra_prose": extra_prose,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-output", required=True)
    parser.add_argument("--raw-output-is-file", action="store_true")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--schema-is-file", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw = load_text(args.raw_output, args.raw_output_is_file)
    schema_text = load_text(args.schema, args.schema_is_file)
    schema = json.loads(schema_text)
    result = validate(raw, schema)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
