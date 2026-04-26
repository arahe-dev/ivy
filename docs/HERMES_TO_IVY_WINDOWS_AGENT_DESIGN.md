# Hermes to IVY Windows Agent Design

## Executive Summary

This document provides a comprehensive research and design analysis for building a Windows-native IVY agent inspired by Hermes Agent. Based on deep investigation of Hermes Agent's architecture, we translate its core concepts into a Windows-native implementation using IVY's existing primitives: Q4_K_M hot-session runner, llama.cpp, PowerShell, and Python.

**Key Findings:**

- Hermes Agent cannot run natively on Windows without WSL2, making direct import infeasible
- Its three-layer memory architecture (frozen snapshot, skills, session search) provides the strongest reference pattern
- The tool registry + schema + validator model is directly applicable to IVY
- Hermes security patterns (dangerous command detection, approval flows) map well to IVY's validator/retry approach
- Phase 1 demo should focus on simulation-only tools before real execution

---

## Part 1: Hermes Agent Deep Dive

### 1.1 What Hermes Agent Is

Hermes Agent is an open-source autonomous AI agent built by Nous Research, designed as "the agent that grows with you." It combines persistent memory, automated skill creation, and multi-platform reach (CLI, Telegram, Discord, Slack) into a single package. The agent runs on Linux, macOS, and WSL2—not natively on Windows.

**Core Philosophy:**

- **Autonomous Operation**: Lives on infrastructure, remembers across sessions, learns from experience
- **Self-Improving**: Creates reusable skills from complex task trajectories
- **Multi-Platform**: Reachable via messaging gateways while working on cloud VMs
- **Memory-First Design**: Three distinct memory layers operating at different timescales

### 1.2 Problems Hermes Solves

| Problem | Hermes Solution |
|---------|----------------|
| Context loss between sessions | Frozen snapshot memory injected at session start |
| Repeated reasoning for common procedures | Automated skill creation after 15+ tool calls |
| Need to recall past conversations | SQLite FTS5 session search |
| Tool schema bloat in prompts | Progressive disclosure (Level 0 names, Level 1 content, Level 2 references) |
| Dangerous command execution | Regex-based pattern matcher with user approval flow |
| Platform lock-in | Unified plugin architecture for memory providers and context engines |
| Cross-session user modeling | Optional external memory providers (Honcho, Mem0, Hindsight) |

### 1.3 Hermes Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Hermes Agent                            │
├─────────────────────────────────────────────────────────────┤
│  CLI / API Server / Gateway (Telegram/Discord/Slack)        │
├─────────────────────────────────────────────────────────────┤
│  AIAgent (run_agent.py) - Orchestration Engine             │
│  ├─ Provider selection (OpenAI, Anthropic, Ollama, etc.)    │
│  ├─ Prompt assembly (SOUL.md, MEMORY.md, skills)          │
│  ├─ Tool execution loop (max_iterations)                  │
│  └─ Result injection + conversation history             │
├─────────────────────────────────────────────────────────────┤
│  Tool Registry (tools/registry.py)                      │
│  └─ 47 tools across 19 toolsets                       │
├─────────────────────────────────────────────────────────────┤
│  Memory System (3 layers)                              │
│  ├─ Layer 1: MEMORY.md + USER.md (frozen snapshot)     │
│  ├─ Layer 2: Skills (episodic, markdown files)        │
│  └─ Layer 3: Session Search (SQLite FTS5)            │
├─────────────────────────────────────────────────────────────┤
│  Execution Backends                                    │
│  └─ Local, Docker, SSH, Daytona, Modal, Singularity     │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Tool System Architecture

**Tool Registry Pattern:**

Each tool file self-registers at import time with:

- `schema`: JSON schema in OpenAI function-calling format
- `handler`: Lambda receiving args dict, returning JSON string
- `check_fn`: Availability check (runs at schema build time)
- `requires_env`: Environment variables required

**Tool Call Flow:**

```
Model → Tool Call (JSON) → Registry.parse() → Validator → check_fn check
    → Handler execution → JSON result → Inject into conversation → Continue loop
```

**Schema Example (weather tool):**

```python
WEATHER_SCHEMA = {
    "name": "weather",
    "description": "Get current weather for a location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or coordinates"
            },
            "units": {
                "type": "string",
                "enum": ["metric", "imperial"],
                "default": "metric"
            }
        },
        "required": ["location"]
    }
}
```

### 1.5 Memory Architecture (Three Layers)

| Layer | Storage | Injection Timing | Purpose |
|-------|---------|------------------|---------|
| Layer 1: Frozen Snapshot | `~/.hermes/memories/MEMORY.md`, `USER.md` | Session start (frozen) | Stable facts, preferences, environment |
| Layer 2: Skills | `~/.hermes/skills/*.md` | On demand (progressive disclosure) | Reusable procedures |
| Layer 3: Session Search | `~/.hermes/state.db` (SQLite FTS5) | On demand | Cross-session recall |

**Progressive Disclosure Pattern:**

- **Level 0**: Skill names + descriptions (~3K tokens for 40+ skills)
- **Level 1**: Full skill content when invoked
- **Level 2**: Reference files, templates, scripts

### 1.6 Security Model

**Dangerous Command Detection:**

Hermes scans terminal commands against regex patterns before execution:

| Pattern Category | Example Patterns |
|------------------|------------------|
| Destructive delete | `rm -r`, `rm -rf`, `del /s /q` |
| Permission escalation | `chmod 777`, `chown -R root` |
| Filesystem wipe | `mkfs`, `dd if=`, `format` |
| SQL destructive | `DROP TABLE`, `DELETE FROM` (no WHERE), `TRUNCATE` |
| System modification | `systemctl stop/disable`, write to `/etc/` |
| Process kill | `kill -9 -1` |
| Code execution | `python -e`, `bash -c`, `curl \| bash` |

**Approval Flow:**

- `on` (default): Prompt user for confirmation
- `auto`: Auto-approve after delay
- `off`: Disable (break-glass)

**Approval Options:**

- Allow this command, this time only
- Allow for session
- Allow always (add to allowlist)
- Deny

### 1.7 What's Valuable for IVY

| Hermes Feature | IVY Relevance | Implementation Notes |
|--------------|--------------|---------------------|
| Tool registry + schema | **High** | Directly applicable to IVY's tool validator |
| Three-layer memory | **High** | Adapt to SQLite + JSON files |
| Progressive disclosure | **Medium** | Relevant for skill loading |
| Dangerous command detection | **High** | Maps to IVY's policy gate |
| Approval flow | **High** | Human-in-loop for high-risk tools |
| Skills system | **Medium** | Later phase, not Phase 1 |
| Session search | **Medium** | SQLite FTS5 for conversation recall |
| Provider abstraction | **Low** | Not needed—fixed llama.cpp backend |

### 1.8 What's Platform-Mismatched for IVY

| Hermes Feature | Why Mismatched | IVY Alternative |
|---------------|----------------|-----------------|
| WSL2 required | Windows-native needs alternative | PowerShell runners |
| Docker backend | Not available | Fixed slot + cache_prompt |
| MCP servers | External dependency | Native Python tools |
| Messaging gateways | Not Phase 1 | Future CLI only |
| Unix socket terminals | Linux-specific | Windows CMD/PowerShell |
| Cron scheduling | Unix crontab | Task Scheduler or manual |
| Unix filesystem paths | Uses `/home/`, `/tmp` | Use `C:\ivy\` paths |

---

## Part 2: Hermes to IVY Translation

### 2.1 Translation Table

| Hermes Concept | What It Does | Why It Exists | Windows-Native IVY Analog | Implementation Notes | Risk |
|---------------|---------------|----------------|---------------------------|----------------------|------|
| AIAgent orchestration | Main agent loop in `run_agent.py` | Coordinates provider, prompts, tools, retries | Q4_K_M hot-session server + Python loop in `run_hot_session.ps1` | Reuse existing hot-session runner, wrap in Python agent class | Low |
| Tool registry | Central tool definitions with `registry.register()` | Enables dynamic tool loading, schema collection | Python registry in `validate_tool_output.py` | Reuse existing validator design, extend with schema | Low |
| Tool schema | JSON schema in OpenAI format | Defines tool interface for model | Already in benchmark YAML files | Extend for all 25 skills | Low |
| Handler | Tool execution function returning JSON string | Isolates tool logic from agent loop | Python functions in `tools/` | Create wrapper functions | Low |
| check_fn | Availability check at schema build time | Filters tools based on dependencies | Policy gate + allowlist | Implement per-skill checks | Medium |
| Layer 1: MEMORY.md | Frozen snapshot memory | Persists stable facts across sessions | JSON config in `manifests/` | Create `session_config.json` | Low |
| Layer 2: Skills | On-demand markdown procedures | Captures reusable trajectories | Future `.md` skill files | Phase 2+ | Low |
| Layer 3: Session Search | SQLite FTS5 conversation index | Enables past session recall | SQLite with FTS5 in `sessions.db` | Store tool calls/results | Medium |
| Dangerous command detection | Regex pattern matching | Prevents destructive commands | Policy gate + pattern list | Extend existing patterns | Low |
| Approval flow | User confirmation for risky tools | Human-in-loop for safety | `ask_user` tool + confirmation | Phase 1 simulation | Medium |
| Provider abstraction | Multi-model support | Flexibility in model choice | Fixed llama.cpp backend | Not needed | Low |
| API server | OpenAI-compatible HTTP endpoint | Enables frontends | llama-server already serves | Future FastAPI bridge | Medium |
| Gateway (Telegram/Discord) | Messaging integration | Multi-platform reach | Future WebSocket UI | Phase 5 | Medium |
| Context files (`AGENTS.md`) | Project-specific context | Shapes agent behavior per project | Static prefix in prompts | Reuse existing prefix | Low |
| Terminal backend | Shell execution (local/Docker/SSH) | Runs commands on host | PowerShell runner | Limited in Phase 1 | **High** |
| Code execution sandbox | Python child process | Safe code execution | Python venv in temp folder | Phase 2+ | **High** |
| Prompt injection scanner | Scans memory/context for injection | Security defense | Policy gate validation | Critical for safety | Critical |

### 2.2 Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                  IVY Windows Agent                           │
├────────────────────────────────────────────────────────────────┤
│  User Interface (Phase 5)                              │
│  └─ CLI / Future Web UI / Future messaging               │
├────────────────────────────────────────────────────────────────┤
│  Agent Loop (Python)                                   │
│  ├─ Static prefix injection                           │
│  ├─ Dynamic task suffix                            │
│  ├─ Tool result injection                          │
│  ├─ Max iterations control (default: 10)            │
│  └─ Stop conditions (stop, error, max_steps)        │
├────────────────────────────────────────────────────────────────┤
│  Tool Validator + Policy Gate                          │
│  ├─ JSON parse validation                          │
│  ├─ Schema validation                            │
│  ├─ Risk classification                          │
│  ├─ Approval check (if high-risk)                │
│  └─ Path restriction enforcement                │
├────────────────────────────────────────────────────────────────┤
│  Tool Registry                                       │
│  ├─ 25 skills with schemas                         │
│  ├─ Handler dispatch                             │
│  └─ Result normalization                        │
├────────────────────────────────────────────────────────────────┤
│  Execution Layer                                     │
│  ├─ Sandbox workspace (local only)              │
│  ├─ Session store (SQLite + JSON)                │
│  └─ Artifact logging                             │
├────────────────────────────────────────────────────────────────┤
│  Model Backend                                       │
│  └─ llama.cpp hot-session server                  │
│     ├─ Fixed id_slot                             │
│     └─ cache_prompt=true                         │
└────────────────────────────────────────────────────────────────┘
```

### 2.3 Component Specifications

#### Model Client

Wraps the Q4_K_M llama-server with:

- Static prefix first (`prompts/static_prefix/ivy_agent_static_prefix.txt`)
- Dynamic task suffix last
- Tool result injection between turns
- Metrics capture: `prompt_n`, `prompt_ms`, `decode_tps`, `cache_reuse_status`

```python
class IvyModelClient:
    def __init__(self, host="localhost", port=8080, slot_id=0):
        self.base_url = f"http://{host}:{port}"
        self.slot_id = slot_id
        
    def chat(self, messages: list, tools: list = None) -> dict:
        # Send to llama-server /v1/chat/completions
        # Return: content, tool_calls, usage
```

#### Tool-Call Validator

Strict validation pipeline:

1. **JSON Parse**: Extract tool_calls from response
2. **Cleaner**: Remove markdown formatting
3. **Schema Validation**: Verify required args present
4. **Failure Taxonomy**: Categorize failures (parse, schema, dangerous, path)
5. **Retry Path**: One retry on invalid output

```python
class ToolValidator:
    def validate(self, response: str) -> list[ToolCall]:
        # Returns validated tool calls
        # Raises ValidationError on failure
        
    def classify_failure(self, error: Exception) -> FailureType:
        # parse_error, schema_error, dangerous_error, path_error
```

#### Policy Gate

Risk classification and enforcement:

```python
class PolicyGate:
    RISK_LEVELS = {
        "low": ["calc_eval", "time_now", "text_transform"],
        "medium": ["fs_list", "fs_read", "fs_write"],
        "high": ["terminal", "run_command", "web_fetch"]
    }
    
    def check(self, tool_call: ToolCall, user_confirmed: bool = False) -> bool:
        # Returns True if allowed
        # False if denied
        # Raises ApprovalRequired if needs confirmation
```

#### Tool Dispatcher

Maps validated calls to handlers:

```python
def dispatch(tool_name: str, args: dict, sandbox: Sandbox) -> str:
    handlers = {
        "calc_eval": lambda a: str(eval(a["expression"])),  # Use safe eval
        "fs_list": lambda a: list_sandbox(a["path"]),
        "fs_read": lambda a: read_sandbox(a["path"]),
        "fs_write": lambda a: write_sandbox(a["path"], a["content"]),
        # ... all 25 skills
    }
    return handlers[tool_name](args)
```

#### Sandbox Workspace

Local folder restrictions:

```
sandbox_workspace/
  in/          # Input fixtures
  out/         # Output artifacts  
  fixtures/   # Test data
  fake_repo/  # Fake git repo
  fake_inbox/ # Fake messages
  fake_web/   # Fake HTML pages
  logs/       # Run logs
```

---

## Part 3: Implementation Phases

### Phase Roadmap

| Phase | Focus | Goal | Timeline | Files |
|-------|-------|------|----------|-------|
| 0 | Research + Design | This document | Complete | 3 docs |
| 1 | Tool simulation | Minimal 5-tool demo | W1 | `run_phase1_demo.ps1` |
| 2 | Real constrained tools | Read-only git, compile check | W2 | `tools/` |
| 3 | Agent loop | Multi-step loop with retry | W3 | `agent_loop.py` |
| 4 | Subagents | Planner/retriever/executor | W4 | `subagents/` |
| 5 | UI/messaging | CLI web UI | W5 | `ui/` |
| 6 | Computer use | Browser sim first | W6 | `browser_sim/` |

### Phase 0: Research and Design

**Deliverables:**

- `docs/HERMES_TO_IVY_WINDOWS_AGENT_DESIGN.md` (this file)
- `docs/IVY_BASIC_SKILLS_25.md`
- `docs/IVY_SIMULATION_ENVIRONMENTS.md`

**Acceptance Criteria:**

- Document comprehensively covers Hermes→IVY translation
- Clear phase roadmap with risk assessments
- Implementation-ready next prompt generated

**Failure Criteria:**

- Cannot proceed without document approval
- No benchmarks to run

### Phase 1: Tool Simulation Only

**Goals:**

- Demonstrate validator + policy gate + 5 tools
- Run in simulation (no real shell/network)
- Showcase 5 demo scenarios

**Implementation Tasks:**

1. Create Python validator module
2. Implement policy gate with risk levels
3. Build 5 simulation tools:
   - `calc_eval` (safe eval)
   - `time_now` (returns timestamp)
   - `text_transform` (case, strip, etc.)
   - `json_validate` (schema check)
   - `ask_user` (simulated confirmation)

4. Create sandbox fixtures
5. Run 5 demo scenarios
6. Log all artifacts

**Acceptance Criteria:**

- All 5 tools execute correctly
- Validator rejects invalid JSON
- Policy gate blocks high-risk without confirmation
- All scenarios pass

**Failure Criteria:**

- Real shell commands execute (security failure)
- Network access occurs (security failure)
- Invalid tool outputs pass

**What NOT to Do:**

- No terminal/shell tools
- No network access
- No browser automation
- No messaging
- No subagents

### Phase 2: Real Constrained Tools

**Goals:**

- Read-only git operations
- Python/PowerShell parse checks
- Safe test execution
- Still no destructive shell

**Implementation Tasks:**

1. Git status/diff read-only tools
2. Python compile check (no execution)
3. PowerShell parse check
4. Sandbox test runner
5. Expanded toolset to 15 skills

**Risk:** Medium (read operations safe, execution requires sandbox)

### Phase 3: Agent Loop

**Goals:**

- Multi-step tool calls
- Tool result injection
- Final answer detection
- Retry on invalid tool output

**Implementation Tasks:**

1. Agent loop with max_steps control
2. Stop conditions: explicit stop, error, max iterations
3. Retry logic (one retry on validation failure)
4. Conversation history management

### Phase 4: Subagents

**Goals:**

- Planner agent (breaks down tasks)
- Retriever agent (finds relevant context)
- Executor agent (runs tools)
- Evaluator agent (checks results)

### Phase 5: Messaging/UI

**Goals:**

- Local CLI interface
- Message preview (not send)
- Future Telegram/Discord integration

### Phase 6: Computer/Browser Use

**Goals:**

- Read-only browser simulation (local HTML)
- Allowlisted web fetch
- Browser automation with no form submission
- Full computer use only with human confirmation

---

## Part 4: Security Model

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
│                  (ultimate authority)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Policy Gate                            │
│         (allows/denies, confirms, logs)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Validator                                │
│            (parses, validates, retries)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Tool Dispatcher                         │
│           (executes only validated calls)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Sandbox Workspace                        │
│          (local folder only, scoped paths)                 │
└─────────────────────────────────────────────────────────────┘
```

### Core Security Rules

1. **Model output is never authority** - Only validated, policy-approved tool calls execute
2. **No raw shell execution** - All commands go through policy gate
3. **Path restrictions enforced** - Sandbox only, no escape to host
4. **Human confirmation required** - For high-risk tools (terminal, network, file write)
5. **Audit logging** - All tool calls, results, approvals logged
6. **Secrets handling** - API keys never logged or injected into prompts
7. **Prompt injection handling** - Input validation + scanning
8. **Stop mechanism** - Emergency stop command available

### Risk Classifications

| Risk Level | Tools | Confirmation Required | Logging |
|-----------|-------|---------------------|---------|
| Low | calc_eval, time_now, text_transform | No | Basic |
| Medium | fs_list, fs_read, fs_write | No (but logged) | Full |
| High | terminal, run_command, web_fetch | **Yes** | Full + approval |

### Dangerous Pattern Detection

Extend Hermes patterns for Windows:

```python
DANGEROUS_PATTERNS = [
    r"rm\s+-r[ft]",           # Unix recursive delete
    r"Remove-Item\s+-Recurse", # PowerShell delete
    r"del\s+/s\s+/q",        # Windows delete
    r"format\s+[a-z]:",       # Format drive
    r"chmod\s+777",           # Unix permissions
    r"icacls\s+.*\/grant",   # Windows permissions
    r"net\s+user",           # User manipulation
    r"New-Object\s+.*Net\.",  # Network objects
    r"Invoke-WebRequest",     # Web fetch (high risk)
    r"iex\s+\(",              # PowerShell iex
]
```

---

## Part 5: Key Questions Answered

### 1. Should IVY Import/Use Hermes Directly?

**Recommendation: No.**

Hermes requires WSL2 or Linux to run natively. While it can connect to a local llama-server, the tool execution layer requires Unix shell commands. Direct import would require significant modification that defeats the purpose.

### 2. Should IVY Copy Hermes Architecture Patterns?

**Recommendation: Yes, selectively.**

The patterns to adopt:

- Tool registry + schema model (directly applicable)
- Three-layer memory (adapt to SQLite + JSON)
- Progressive disclosure (for skills)
- Dangerous command detection (extend for Windows)
- Approval flow (for high-risk tools)

The patterns to avoid:

- WSL2 dependency (use PowerShell instead)
- Docker backend (use fixed slot + cache)
- Unix-specific paths (use Windows paths)

### 3. What Does Hermes Do That IVY Should Not Rebuild Yet?

- **Skills system**: Not Phase 1; postpone until tool loop proven
- **MCP integration**: External dependency, not needed
- **Messaging gateways**: Future phase only
- **Cron scheduling**: Use Task Scheduler or manual
- **Container backends**: Not required for local use

### 4. What Does IVY Need That Hermes Does Not Handle Exactly?

- **Hot-session runner**: Hermes re-reads memory each session; IVY needs fixed slot + cache
- **Windows paths**: Hermes assumes Unix paths
- **PowerShell tools**: Hermes uses bash/sh
- **Q4_K_M constraints**: Token budget, retry logic for tool calling

### 5. What Is the Smallest Safe Demo Worth Building?

Phase 1: 5-tool simulation demo

- calc_eval, time_now, text_transform, json_validate, ask_user
- Validator + policy gate
- 5 sandbox scenarios
- Artifact logging

### 6. What Is the First Thing That Would Prove This Is Real?

A working Phase 1 demo where:

1. User submits a task requiring multiple tool calls
2. Model generates valid JSON tool calls
3. Validator parses and validates them
4. Policy gate checks risk levels
5. Tools execute in sandbox
6. Results inject back to model
7. Final answer generated

### 7. What Would Be Overbuilding Right Now?

- Full skills system (need proven tool loop first)
- Subagents (start with single-agent loop)
- Real browser automation (start with simulation)
- Messaging integrations (no gateway until loop proven)
- Database migrations (start with JSON, migrate later)

### 8. How Do We Extend from Tool Use to Agency?

Tool use: Single tool call, no loop
Agency: Multi-step loop with:

- Planning (model decides to use tools)
- Execution (tools run, results return)
- Evaluation (model assesses results)
- Continuation (model decides next step or stops)

### 9. How Do We Extend from Agency to Subagents?

Subagents: Specialized agents for specific tasks

- Planner: Decomposes user task into steps
- Retriever: Finds relevant context
- Executor: Runs tools
- Evaluator: Checks work quality

Each has smaller tool scope (principle of least privilege)

### 10. How Do We Extend from Subagents to Computer Use?

Computer use: Agent controls browser/input devices

Read-only first:

- Browser simulation (local HTML fixtures)
- Allowlisted web fetch only
- No form submission

Then controlled automation:

- Browser automation with human confirmation
- Audit logging of all actions
- No persistence of credentials

### 11. How Do We Add Messaging Safely?

1. **Phase 5**: Local CLI only (no external)
2. **Phase 5+**: Message preview (draft, do not send)
3. **Phase 6+**: Allowlisted senders only
4. **Ongoing**: All messages logged, human confirmation for external

### 12. What Should Be Benchmarked vs. What Should Be Qualitatively Inspected?

**Benchmark:**

- Tool call accuracy (already validated: 96% raw, 100% after retry)
- Token throughput (already ~32 tok/s baseline)
- Cache reuse rate (already proven: ~97.6% repeat, ~45.4% changed-tail)
- 25 skill execution success

**Qualitatively Inspected:**

- Safety of pattern detection
- Usability of approval flow
- Quality of skill documents
- Appropriateness of memory layer

---

## Part 6: Next Implementation Prompt

### NEXT IMPLEMENTATION PROMPT: Build IVY Phase 1 Tool Simulation Demo

**Instructions:**

Build only Phase 1 of the Windows-native IVY agent:

1. **Do NOT install Hermes** - No WSL, no Docker, no Unix shell
2. **Do NOT implement real shell tools** - Simulation only for Phase 1
3. **Do NOT implement network tools** - No web fetch, no browser
4. **Do NOT implement subagents** - Single-agent loop only

**Requirements:**

Create the following components:

1. **Python validator module** (`ivy_validator.py`)
   - JSON parse validation
   - Schema validation against tool definitions
   - Failure classification
   - Retry logic (one retry on invalid)

2. **Policy gate** (`ivy_policy.py`)
   - Risk level classification (low/medium/high)
   - Path restriction enforcement
   - Confirmation requirement check

3. **Five simulation tools** (`tools/simulation/`)
   - `calc_eval`: Safe mathematical expression evaluation
   - `time_now`: Current timestamp
   - `text_transform`: Case, strip, normalize operations
   - `json_validate`: JSON syntax + optional schema check
   - `ask_user`: Simulated user confirmation

4. **Sandbox fixtures** (`sandbox_workspace/`)
   - Input fixtures in `in/`
   - Output artifacts in `out/`
   - Test data in `fixtures/`

5. **Five demo scenarios** (`scenarios/`)
   - Scenario 1: Calculate and transform
   - Scenario 2: Validate JSON from fixture
   - Scenario 3: Ask user for confirmation (simulated)
   - Scenario 4: Multi-tool sequence
   - Scenario 5: Invalid tool call handling

6. **Runner script** (`run_phase1_demo.ps1`)
   - Starts hot-session server
   - Loads tool schemas
   - Runs scenarios
   - Collects artifacts

**Tool Schema Format:**

Each tool must define:

```python
TOOL_SCHEMA = {
    "name": "tool_name",
    "description": "What the tool does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}
```

**Acceptance Criteria:**

- All 5 tools execute correctly in sandbox
- Validator rejects malformed JSON
- Policy gate blocks dangerous patterns
- At least 4/5 scenarios pass
- All artifacts logged

**Deliverables:**

- `ivy_validator.py`
- `ivy_policy.py`
- `tools/simulation/*.py`
- `sandbox_workspace/**`
- `scenarios/*.json`
- `run_phase1_demo.ps1`
- `docs/PHASE1_RESULTS.md`

---

## Appendix: Hermes Reference Links

- **Main Repository**: https://github.com/nousresearch/hermes-agent
- **Documentation**: https://hermes-agent.nousresearch.com/docs/
- **Architecture**: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/
- **Tool System**: https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools
- **Security**: https://nousresearch-hermes-agent.mintlify.app/user-guide/security
- **Memory System**: https://hermes-agent.ai/blog/hermes-agent-memory-system
- **Skills System**: https://hermify.io/en/blog/hermes-agent-memory-and-skills

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-26 | Initial research and design document |

---

*Generated for IVY Windows Agent Project*