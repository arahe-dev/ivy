import json


TOOL_SCHEMAS = {
    "calc_eval": {
        "description": "Evaluate a simple arithmetic expression.",
        "properties": {
            "expr": {"type": "string"},
        },
        "required": ["expr"],
        "additional_properties": False,
    },
    "json_validate": {
        "description": "Validate JSON syntax.",
        "properties": {
            "json_text": {"type": "string"},
        },
        "required": ["json_text"],
        "additional_properties": False,
    },
    "fs_list": {
        "description": "List files under sandbox workspace.",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
        "additional_properties": False,
    },
    "fs_read": {
        "description": "Read a file under sandbox workspace.",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
        "additional_properties": False,
    },
    "fs_write": {
        "description": "Write a file under sandbox_workspace/out.",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "mode": {"type": "string", "enum": ["overwrite", "append"]},
        },
        "required": ["path", "content", "mode"],
        "additional_properties": False,
    },
    "ask_user": {
        "description": "Ask user for clarification or confirmation (simulated in Phase 1).",
        "properties": {
            "question": {"type": "string"},
        },
        "required": ["question"],
        "additional_properties": False,
    },
}


ALLOWED_TOOLS = tuple(TOOL_SCHEMAS.keys())


def tools_prompt_json() -> str:
    prompt_shape = {
        name: {
            "description": schema["description"],
            "arguments": schema["properties"],
            "required": schema["required"],
        }
        for name, schema in TOOL_SCHEMAS.items()
    }
    return json.dumps(prompt_shape, indent=2, ensure_ascii=True)


def response_contract_text() -> str:
    return (
        "Output exactly one JSON object and nothing else. Allowed outputs:\n"
        "1) Tool call: {\"tool\":\"tool_name\",\"arguments\":{...}}\n"
        "2) Final answer: {\"final\":\"...\"}\n"
        "No markdown fences. No <think> tags. No extra prose."
    )
