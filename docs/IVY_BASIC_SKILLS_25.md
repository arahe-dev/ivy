# IVY 25 Basic Skills

## Overview

This document defines the 25 essential skills/tools for the Windows-native IVY agent. Each skill is specified with purpose, tool schema, risk level, implementation notes, and test criteria.

**Organizing Principles:**

- Skills organized by category (A-E)
- Each skill has clear risk classification
- Phase 1 includes only categories A + B simulation tools
- Categories C-F are Phase 2+ as skills are proven
- No arbitrary shell execution in any phase

---

## Skill Categories

| Category | Skills | Focus | Phase |
|----------|--------|-------|-------|
| A | 1-5 | Pure computation | 1 |
| B | 6-12 | Filesystem sandbox | 1-2 |
| C | 13-17 | Repo/dev inspection | 2 |
| D | 18-22 | Planning/session | 2 |
| E | 23-25 | External/computer-use-adjacent | 2+ (simulated) |

---

## Category A: Pure Low-Risk Computation Tools (1-5)

### Skill 1: calc_eval

| Attribute | Value |
|-----------|-------|
| Name | calc_eval |
| Purpose | Safe mathematical expression evaluation |
| Schema | `{"expression": "string"}` |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "calc_eval",
    "description": "Evaluate a mathematical expression. Only supports basic arithmetic: +, -, *, /, **, %, and parentheses. No variables, no functions, no side effects.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5', '(3 + 4) ** 2')"
            }
        },
        "required": ["expression"]
    }
}
```

**Implementation:**

```python
def calc_eval(expression: str) -> str:
    # Whitelist only: digits, +, -, *, /, **, %, (, )
    allowed = set("0123456789+-*/%() ")
    if not all(c in allowed for c in expression):
        return json.dumps({"error": "Invalid characters in expression"})
    try:
        result = eval(expression)
        return json.dumps({"result": result, "expression": expression})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

**Test Scenarios:**

| Input | Expected Output |
|-------|----------------|
| `"2 + 2"` | `{"result": 4}` |
| `"10 * 5"` | `{"result": 50}` |
| `"(3 + 4) ** 2"` | `{"result": 49}` |
| `"1 / 3"` | `{"result": 0.3333...}` |
| `"10 / 0"` | `{"error": "division by zero"}` |

**Safety Boundaries:**

- No variables (`x = 5` → error)
- No functions (`len("")` → error)
- No imports (`import os` → error)
- No attribute access (`(1).__class__` → error)

**What Could Go Wrong:**

- Expression injection via eval → use whitelist
- Infinite loop → timeout after 1 second

---

### Skill 2: time_now

| Attribute | Value |
|-----------|-------|
| Name | time_now |
| Purpose | Return current timestamp and formatted time |
| Schema | `{}` (no parameters) |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "time_now",
    "description": "Get the current timestamp and formatted time. Returns UTC and local time.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}
```

**Implementation:**

```python
from datetime import datetime, timezone

def time_now() -> str:
    now = datetime.now(timezone.utc)
    return json.dumps({
        "utc_iso": now.isoformat(),
        "utc_timestamp": now.timestamp(),
        "local_iso": datetime.now().isoformat(),
        "local_readable": now.strftime("%Y-%m-%d %H:%M:%S UTC")
    })
```

**Test Scenarios:**

| Input | Expected Output |
|-------|----------------|
| `{}` | Valid timestamp, ISO format |

---

### Skill 3: text_transform

| Attribute | Value |
|-----------|-------|
| Name | text_transform |
| Purpose | Text case, strip, and normalization operations |
| Schema | `{"text": "string", "operation": "string (upper/lower/title/strip/reverse/word_count/char_count)"}` |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "text_transform",
    "description": "Transform text with case operations, stripping, or counting. Operations: upper, lower, title, strip, reverse, word_count, char_count.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text"},
            "operation": {
                "type": "string",
                "enum": ["upper", "lower", "title", "strip", "reverse", "word_count", "char_count"],
                "description": "Transformation operation"
            }
        },
        "required": ["text", "operation"]
    }
}
```

**Implementation:**

```python
def text_transform(text: str, operation: str) -> str:
    ops = {
        "upper": lambda t: t.upper(),
        "lower": lambda t: t.lower(),
        "title": lambda t: t.title(),
        "strip": lambda t: t.strip(),
        "reverse": lambda t: t[::-1],
        "word_count": lambda t: len(t.split()),
        "char_count": lambda t: len(t),
    }
    if operation not in ops:
        return json.dumps({"error": f"Unknown operation: {operation}"})
    return json.dumps({"result": ops[operation](text), "input": text, "operation": operation})
```

---

### Skill 4: json_validate

| Attribute | Value |
|-----------|-------|
| Name | json_validate |
| Purpose | Validate JSON syntax and optional schema |
| Schema | `{"json_str": "string", "schema": "object (optional)"}` |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "json_validate",
    "description": "Validate JSON syntax. Optionally validate against a simple schema (type checks for keys).",
    "parameters": {
        "type": "object",
        "properties": {
            "json_str": {"type": "string", "description": "JSON string to validate"},
            "schema": {"type": "object", "description": "Optional schema for validation (keys and expected types)", "default": {}}
        },
        "required": ["json_str"]
    }
}
```

**Implementation:**

```python
import json as json_module
import re

def json_validate(json_str: str, schema: dict = None) -> str:
    try:
        data = json_module.loads(json_str)
    except json_module.JSONDecodeError as e:
        return json.dumps({"valid": False, "error": str(e)})
    
    if schema:
        # Simple schema validation: check required keys and types
        for key, expected_type in schema.items():
            if key not in data:
                return json.dumps({"valid": False, "error": f"Missing key: {key}"})
            if not isinstance(data[key], expected_type):
                return json.dumps({"valid": False, "error": f"Key {key} should be {expected_type}, got {type(data[key]).__name__}"})
    
    return json.dumps({"valid": True, "data": data})
```

---

### Skill 5: regex_extract

| Attribute | Value |
|-----------|-------|
| Name | regex_extract |
| Purpose | Extract patterns from text using regex |
| Schema | `{"text": "string", "pattern": "string"}` |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

**Schema:**

```python
{
    "name": "regex_extract",
    "description": "Extract all matches of a regex pattern from text. Returns list of matches.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text to search"},
            "pattern": {"type": "string", "description": "Regex pattern (Python syntax)"}
        },
        "required": ["text", "pattern"]
    }
}
```

**Implementation:**

```python
import re

def regex_extract(text: str, pattern: str) -> str:
    try:
        matches = re.findall(pattern, text)
        return json.dumps({"matches": matches, "count": len(matches)})
    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {e}"})
```

**Safety:**

- No regex denial-of-service (limit to 1000 chars, timeout 1s)

---

## Category B: Filesystem Sandbox Tools (6-12)

### Skill 6: fs_list

| Attribute | Value |
|-----------|-------|
| Name | fs_list |
| Purpose | List files in sandbox directory |
| Schema | `{"path": "string (relative to sandbox)"}` |
| Risk Level | **Medium** |
| Phase 1 | ✅ Yes (simulation) |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "fs_list",
    "description": "List files and directories in a path relative to the sandbox workspace. Use '/' for paths.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from sandbox root (e.g., 'fixtures/', 'out/')"}
        },
        "required": ["path"]
    }
}
```

**Implementation:**

```python
import os

SANDBOX_ROOT = "sandbox_workspace"

def fs_list(path: str) -> str:
    # Resolve full path
    full_path = os.path.join(SANDBOX_ROOT, path.lstrip("/"))
    
    # Security: ensure still in sandbox
    real_root = os.path.realpath(SANDBOX_ROOT)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_root):
        return json.dumps({"error": "Path outside sandbox"})
    
    if not os.path.exists(full_path):
        return json.dumps({"error": "Path does not exist"})
    
    entries = []
    for name in os.listdir(full_path):
        full_name = os.path.join(full_path, name)
        entries.append({
            "name": name,
            "type": "dir" if os.path.isdir(full_name) else "file"
        })
    
    return json.dumps({"entries": entries, "path": path})
```

---

### Skill 7: fs_read

| Attribute | Value |
|-----------|-------|
| Name | fs_read |
| Purpose | Read file contents from sandbox |
| Schema | `{"path": "string (relative to sandbox)"}` |
| Risk Level | **Medium** |
| Phase 1 | ✅ Yes (simulation) |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "fs_read",
    "description": "Read the contents of a file in the sandbox workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from sandbox root"}
        },
        "required": ["path"]
    }
}
```

**Implementation:**

```python
import os

def fs_read(path: str) -> str:
    full_path = os.path.join(SANDBOX_ROOT, path.lstrip("/"))
    
    # Security: ensure still in sandbox
    real_root = os.path.realpath(SANDBOX_ROOT)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_root):
        return json.dumps({"error": "Path outside sandbox"})
    
    if not os.path.exists(full_path):
        return json.dumps({"error": "File does not exist"})
    
    if not os.path.isfile(full_path):
        return json.dumps({"error": "Path is not a file"})
    
    # Limit file size (100KB max)
    size = os.path.getsize(full_path)
    if size > 100_000:
        return json.dumps({"error": "File too large"})
    
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return json.dumps({"content": content, "path": path, "size": size})
```

---

### Skill 8: fs_write

| Attribute | Value |
|-----------|-------|
| Name | fs_write |
| Purpose | Write content to file in sandbox output folder |
| Schema | `{"path": "string", "content": "string"}` |
| Risk Level | **Medium** |
| Phase 1 | ✅ Yes (to out/ only) |
| Confirmation | No |
| Priority | P0 |

**Schema:**

```python
{
    "name": "fs_write",
    "description": "Write content to a file in the sandbox workspace. In Phase 1, only writes to 'out/' directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path (must start with 'out/')"},
            "content": {"type": "string", "description": "Content to write"}
        },
        "required": ["path", "content"]
    }
}
```

---

### Skill 9: fs_append

| Attribute | Value |
|-----------|-------|
| Name | fs_append |
| Purpose | Append content to file in sandbox |
| Schema | `{"path": "string", "content": "string"}` |
| Risk Level | **Medium** |
| Phase 1 | ✅ Yes (to out/ only) |
| Confirmation | No |
| Priority | P1 |

---

### Skill 10: fs_copy_within_sandbox

| Attribute | Value |
|-----------|-------|
| Name | fs_copy_within_sandbox |
| Purpose | Copy file within sandbox |
| Schema | `{"source": "string", "destination": "string"}` |
| Risk Level | **Medium** |
| Phase 1 | ❌ No |
| Confirmation | No |
| Priority | P2 |

---

### Skill 11: fs_search_text

| Attribute | Value |
|-----------|-------|
| Name | fs_search_text |
| Purpose | Search for text in sandbox files |
| Schema | `{"query": "string", "path": "string (optional)"}` |
| Risk Level | **Medium** |
| Phase 1 | ❌ No |
| Confirmation | No |
| Priority | P1 |

---

### Skill 12: fs_apply_patch_to_sandbox_file

| Attribute | Value |
|-----------|-------|
| Name | fs_apply_patch_to_sandbox_file |
| Purpose | Apply a simple patch to a file |
| Schema | `{"path": "string", "patch": "string"}` |
| Risk Level | **Medium** |
| Phase 1 | ❌ No |
| Confirmation | **Yes** |
| Priority | P2 |

---

## Category C: Repo/Dev Inspection Tools (13-17)

### Skill 13: git_status_readonly

| Attribute | Value |
|-----------|-------|
| Name | git_status_readonly |
| Purpose | Read git status (no modifications) |
| Schema | `{}` |
| Risk Level | **Medium** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

**Schema:**

```python
{
    "name": "git_status_readonly",
    "description": "Run 'git status --short' to see modified files. Read-only operation.",
    "parameters": {"type": "object", "properties": {}}
}
```

---

### Skill 14: git_diff_readonly

| Attribute | Value |
|-----------|-------|
| Name | git_diff_readonly |
| Purpose | Read git diff (no modifications) |
| Schema | `{"files": "array (optional)"}` |
| Risk Level | **Medium** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

### Skill 15: run_tests_sandboxed

| Attribute | Value |
|-----------|-------|
| Name | run_tests_sandboxed |
| Purpose | Run tests in sandboxed environment |
| Schema | `{"test_path": "string"}` |
| Risk Level | **Medium** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

### Skill 16: python_lint_or_compile

| Attribute | Value |
|-----------|-------|
| Name | python_lint_or_compile |
| Purpose | Syntax check Python without execution |
| Schema | `{"file_path": "string"}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

### Skill 17: powershell_parse_check

| Attribute | Value |
|-----------|-------|
| Name | powershell_parse_check |
| Purpose | Parse check PowerShell script without execution |
| Schema | `{"file_path": "string"}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

## Category D: Planning/Session Tools (18-22)

### Skill 18: ask_user

| Attribute | Value |
|-----------|-------|
| Name | ask_user |
| Purpose | Request user confirmation or input |
| Schema | `{"question": "string", "options": "array (optional)"}` |
| Risk Level | **Low** |
| Phase 1 | ✅ Yes (simulated) |
| Confirmation | **Yes** (human required) |
| Priority | P0 |

---

### Skill 19: create_todo

| Attribute | Value |
|-----------|-------|
| Name | create_todo |
| Purpose | Create a todo item in session store |
| Schema | `{"title": "string", "description": "string"}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

### Skill 20: update_todo

| Attribute | Value |
|-----------|-------|
| Name | update_todo |
| Purpose | Update todo status |
| Schema | `{"id": "string", "status": "string (in_progress/completed)"}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P1 |

---

### Skill 21: summarize_session

| Attribute | Value |
|-----------|-------|
| Name | summarize_session |
| Purpose | Summarize current session context |
| Schema | `{}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P2 |

---

### Skill 22: retrieve_session_note

| Attribute | Value |
|-----------|-------|
| Name | retrieve_session_note |
| Purpose | Retrieve previous session notes |
| Schema | `{"query": "string"}` |
| Risk Level | **Low** |
| Phase 2 | ✅ Yes |
| Confirmation | No |
| Priority | P2 |

---

## Category E: External/Computer-Use-Adjacent Tools (23-25)

### Skill 23: web_fetch_allowlisted

| Attribute | Value |
|-----------|-------|
| Name | web_fetch_allowlisted |
| Purpose | Fetch content from allowlisted URLs only |
| Schema | `{"url": "string"}` |
| Risk Level | **High** |
| Phase 2 | ❌ No (simulated) |
| Confirmation | **Yes** |
| Priority | P1 |

**Note:** In Phase 2, this is simulated - fetches local fake_web fixtures only.

.allowlist = ["localhost", "127.0.0.1", "example.com"]

---

### Skill 24: browser_readonly_page

| Attribute | Value |
|-----------|-------|
| Name | browser_readonly_page |
| Purpose | Read content from saved HTML fixtures |
| Schema | `{"fixture": "string"}` |
| Risk Level | **Medium** |
| Phase 2 | ✅ Yes (simulated) |
| Confirmation | No |
| Priority | P1 |

---

### Skill 25: message_preview_send_later

| Attribute | Value |
|-----------|-------|
| Name | message_preview_send_later |
| Purpose | Draft message for preview, defer actual send |
| Schema | `{"recipient": "string", "message": "string", "channel": "string"}` |
| Risk Level | **High** |
| Phase 2 | ✅ Yes (simulated - preview only) |
| Confirmation | **Yes** (for real send) |
| Priority | P2 |

**Note:** Phase 2 simulation writes to fake_inbox, does not send.

---

## Risk Level Summary

| Risk Level | Skills | Confirmation Required |
|-----------|--------|---------------------|
| Low | 1-5, 16, 17, 18-22 | No |
| Medium | 6-15, 24 | No (but logged) |
| High | 23, 25 | **Yes** |

---

## Phase 1 Skill Subset

For Phase 1 implementation, these skills are included:

| # | Skill | Risk | Phase 1 Status |
|---|-------|------|----------------|
| 1 | calc_eval | Low | ✅ |
| 2 | time_now | Low | ✅ |
| 3 | text_transform | Low | ✅ |
| 4 | json_validate | Low | ✅ |
| 5 | regex_extract | Low | ✅ |
| 6 | fs_list | Medium | ✅ (to fixtures/) |
| 7 | fs_read | Medium | ✅ (from fixtures/) |
| 8 | fs_write | Medium | ✅ (to out/ only) |
| 9 | fs_append | Medium | ❌ (Phase 2) |
| 10 | fs_copy_within_sandbox | Medium | ❌ (Phase 2) |
| 11 | fs_search_text | Medium | ❌ (Phase 2) |
| 12 | fs_apply_patch | Medium | ❌ (Phase 2) |
| 13 | git_status_readonly | Medium | ❌ (Phase 2) |
| 14 | git_diff_readonly | Medium | ❌ (Phase 2) |
| 15 | run_tests | Medium | ❌ (Phase 2) |
| 16 | python_lint | Low | ❌ (Phase 2) |
| 17 | powershell_parse | Low | ❌ (Phase 2) |
| 18 | ask_user | Low | ✅ (simulated) |
| 19 | create_todo | Low | ❌ (Phase 2) |
| 20 | update_todo | Low | ❌ (Phase 2) |
| 21 | summarize_session | Low | ❌ (Phase 2) |
| 22 | retrieve_session | Low | ❌ (Phase 2) |
| 23 | web_fetch | High | ❌ (Phase 2+) |
| 24 | browser_readonly | Medium | ❌ (Phase 2+) |
| 25 | message_preview | High | ❌ (Phase 2+) |

---

## Test Priority Mapping

| Priority | Skills | Criteria |
|-----------|--------|----------|
| P0 | 1-4, 6-8, 18 | Must work in Phase 1 demo |
| P1 | 5, 15-17, 19-24 | Must work in Phase 2 |
| P2 | 9-14, 25 | Must work in Phase 3 |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-26 | Initial 25 skills document |

---

*Generated for IVY Windows Agent Project*