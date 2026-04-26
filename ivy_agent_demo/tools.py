from __future__ import annotations

import ast
import json
import operator
from pathlib import Path
from typing import Any


MAX_READ_BYTES = 100 * 1024


class ToolExecutionError(Exception):
    pass


def _json_result(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def _safe_read_text(path: Path) -> str:
    data = path.read_bytes()
    if len(data) > MAX_READ_BYTES:
        raise ToolExecutionError("File exceeds 100 KB limit")
    return data.decode("utf-8")


def tool_json_validate(arguments: dict[str, Any]) -> dict[str, Any]:
    json_text = arguments["json_text"]
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return _json_result(
            {
                "ok": False,
                "valid": False,
                "error": str(exc),
            }
        )
    return _json_result(
        {
            "ok": True,
            "valid": True,
            "type": type(parsed).__name__,
        }
    )


def tool_fs_list(arguments: dict[str, Any]) -> dict[str, Any]:
    path = Path(arguments["path"])
    if not path.exists():
        return _json_result({"ok": False, "error": "Path does not exist"})
    if not path.is_dir():
        return _json_result({"ok": False, "error": "Path is not a directory"})
    entries = []
    for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        entries.append(
            {
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
    return _json_result({"ok": True, "path": str(path), "entries": entries})


def tool_fs_read(arguments: dict[str, Any]) -> dict[str, Any]:
    path = Path(arguments["path"])
    if not path.exists():
        return _json_result({"ok": False, "error": "File does not exist"})
    if not path.is_file():
        return _json_result({"ok": False, "error": "Path is not a file"})
    try:
        content = _safe_read_text(path)
    except UnicodeDecodeError:
        return _json_result({"ok": False, "error": "File is not UTF-8 text"})
    except ToolExecutionError as exc:
        return _json_result({"ok": False, "error": str(exc)})
    return _json_result(
        {
            "ok": True,
            "path": str(path),
            "size": path.stat().st_size,
            "content": content,
        }
    )


def tool_fs_write(arguments: dict[str, Any]) -> dict[str, Any]:
    path = Path(arguments["path"])
    mode = arguments["mode"]
    content = arguments["content"]

    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "overwrite":
        path.write_text(content, encoding="utf-8")
    elif mode == "append":
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        return _json_result({"ok": False, "error": "Invalid mode"})

    return _json_result(
        {
            "ok": True,
            "path": str(path),
            "mode": mode,
            "bytes_written": len(content.encode("utf-8")),
        }
    )


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_expr_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_expr_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPERATORS:
            raise ToolExecutionError("Unsupported operator")
        return _BINARY_OPERATORS[op_type](_eval_expr_node(node.left), _eval_expr_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPERATORS:
            raise ToolExecutionError("Unsupported unary operator")
        return _UNARY_OPERATORS[op_type](_eval_expr_node(node.operand))
    raise ToolExecutionError("Unsafe expression")


def tool_calc_eval(arguments: dict[str, Any]) -> dict[str, Any]:
    expr = arguments["expr"]
    if not expr.strip():
        return _json_result({"ok": False, "error": "Expression is empty"})
    try:
        tree = ast.parse(expr, mode="eval")
        value = _eval_expr_node(tree)
    except ZeroDivisionError:
        return _json_result({"ok": False, "error": "Division by zero"})
    except (SyntaxError, ToolExecutionError) as exc:
        return _json_result({"ok": False, "error": str(exc)})
    except Exception:
        return _json_result({"ok": False, "error": "Evaluation failed"})

    if value.is_integer():
        numeric: int | float = int(value)
    else:
        numeric = round(value, 10)

    return _json_result({"ok": True, "expr": expr, "result": numeric})


def tool_ask_user(arguments: dict[str, Any]) -> dict[str, Any]:
    question = arguments["question"]
    question_lower = question.lower()
    if "which" in question_lower or "inspect" in question_lower or "choose" in question_lower:
        simulated_answer = "Simulated user response: no selection provided yet; stop and present the choices to the user."
    elif "delete" in question_lower or "remove" in question_lower:
        simulated_answer = "Simulated user response: no; do not perform destructive actions."
    else:
        simulated_answer = "Simulated user response: proceed only if the next action is safe and within policy."
    return _json_result(
        {
            "ok": True,
            "question": question,
            "simulated": True,
            "answer": simulated_answer,
        }
    )


def dispatch_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "calc_eval":
        return tool_calc_eval(arguments)
    if tool_name == "json_validate":
        return tool_json_validate(arguments)
    if tool_name == "fs_list":
        return tool_fs_list(arguments)
    if tool_name == "fs_read":
        return tool_fs_read(arguments)
    if tool_name == "fs_write":
        return tool_fs_write(arguments)
    if tool_name == "ask_user":
        return tool_ask_user(arguments)
    return {"ok": False, "error": f"Unknown tool: {tool_name}"}
