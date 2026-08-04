# REPL.io — Agent Guide

## Project

A terminal-based **agentic REPL core**. The model is the planner; the tool registry is how it acts. It is a zero-dependency Python app (`stdlib only`) built around a **single agent loop**: one SSE stream per turn where the model either emits content or requests tool calls, which the loop executes and feeds back until the model answers.

Multi-provider chat, web search, sessions, slash commands, and (planned) machine access, personas, delegation, and plugins are all capabilities on top of that core.

## Tech Stack

- Python >=3.10, **stdlib only** (no external dependencies)
- `readline` — input history + tab completion for slash commands
- `urllib.request` — HTTP + SSE streaming
- `urllib.error` — HTTP error handling
- `json` / `pathlib` / `os` — config and session storage

## Architecture: Agentic Core

The agentic core has three layers:

1. **Agent loop** (`chat.py`) — the orchestration. Each turn runs a single streaming request. The provider's `chat()` is a generator yielding events, and the loop reacts:
   - `thinking` / `token` — streamed to the terminal (dimmed thinking, optional markdown)
   - `tool_calls` — append the assistant message, execute each call, append `tool` results, then continue the loop
   - `error` — print and bail
   - `done` — persist the assistant message (timestamp/duration/model) and stop
   
   One stream, one round trip when no tools are used. `chat_nonstreaming()` is reserved for query refinement, not the main path.

2. **ToolRegistry** (`tools/registry.py`) — the **single dispatch point**. The model invokes tools via OpenAI function calling; slash commands are thin wrappers that call the same `execute()`. The loop never special-cases tool names — per-tool behavior comes from registration metadata (`refine`, later `confirm`).

3. **Commands** (`commands/`) — user-facing affordances. A command either wraps a tool or performs a local action (`/model`, `/session`).

Providers (`providers/`) are OpenAI-compatible `/v1/chat/completions` backends that implement the event-generator `chat()` contract.

### Project Structure

```
repl.io/
├── pyproject.toml
├── AGENTS.md
├── README.md
├── TODO.md
├── CHANGELOG.md
├── tests/
│   └── test_tool_calling.py   # Mock tests (no network/API key needed)
├── src/replio/
│   ├── __init__.py
│   ├── __main__.py          # python -m replio
│   ├── main.py              # CLI arg parsing + bootstrap
│   ├── config.py            # JSON config (global + local merge)
│   ├── chat.py              # Agent loop + REPL with readline
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract provider (OpenAI-compatible)
│   │   └── ollama.py        # Ollama cloud via /v1/chat/completions
│   ├── sessions/
│   │   ├── __init__.py
│   │   └── manager.py       # Session CRUD (JSON files)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── registry.py      # Command registration + dispatch
│   │   └── builtins.py      # /help, /connect, /model, /session, etc.
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py      # Tool registration + dispatch (OpenAI function calling)
│   │   ├── policy.py        # ToolPolicy — allow/ask/deny permissions + path scoping
│   │   ├── builtins.py      # web_search, fetch_page tools
│   │   └── machine.py       # read_file, list_dir, write_file, run_command tools
│   ├── web/
│   │   ├── __init__.py
│   │   ├── search.py        # DuckDuckGo Lite search via html.parser
│   │   └── display.py       # Terminal formatting + context injection
│   └── utils/
│       ├── __init__.py
│       └── http.py          # urllib-based SSE streaming
```

## Conventions

### Code Style
- No external dependencies — stdlib only
- No comments in code
- Type hints required for all function signatures
- Use `from __future__ import annotations` if needed for `|` syntax
- Prefer `pathlib.Path` over `os.path`
- ANSI escape codes for terminal coloring (no `rich`/`colorama`)
- `\001` / `\002` readline markers around ANSI codes in prompts

### Architecture Rules
- One agent loop, one SSE stream per turn — no separate non-streaming decision round
- `ToolRegistry` is the single dispatch point: commands call tools, they never reimplement them
- No tool-name special-casing in the loop — use registration metadata instead
- `BaseProvider.chat()` is a generator yielding events: `thinking`, `token`, `tool_calls`, `error`, `done`
- `BaseProvider` uses OpenAI-compatible `/v1/chat/completions` format
- Config: global (`~/.config/replio/config.json`) → local (`.replio/config.json`) merge, local wins
- Sessions stored as `.replio/sessions/<name>.json`
- Slash commands registered via `@registry.register()` decorator
- Tools registered via `@tool_registry.register()` decorator (OpenAI function calling format)

### Doc Conventions
- `TODO.md` is grouped by **feature sections**. `## Ideas` sits at the top for visibility; current work and planned features follow; older feature groups stay below; `## REPL & Core` forms the ground (bottom) section — current state stays readable with `head`. Unfinished tasks remain in their group. Completed items are marked `[x]` **inline in their group** — do not flatten the list or move history into an archive section.
- `CHANGELOG.md` is grouped by **versions**, newest at the top — new `## vX.Y.Z — YYYY-MM-DD` sections go above previous ones, so the latest changes are readable with `head`. Entries under each version are grouped by `### Added` / `### Changed` / `### Removed`, and **within each group the newest entry comes first**.
- After completing a planned task: mark it `[x]` in `TODO.md` and add entries under the current version section at the top of `CHANGELOG.md` (start a new version section first if none exists).
- Keep both files in sync with actual project state.

## Extension Points

### Adding a Tool
1. Open `tools/builtins.py` (web tools) or `tools/machine.py` (file/exec tools)
2. Use `@registry.register(name, description, parameters)` decorator
3. `parameters` follow the OpenAI function calling JSON schema format
4. Handler receives keyword arguments matching the schema
5. Return a string (the tool result injected into the conversation)
6. Add optional metadata for loop behavior — e.g. `refine=True` to auto-refine short query args via a lightweight model call (gated by the `query_refine` config)
7. Optional permission/display metadata: `category` (`search`/`read`/`write`/`exec`/`ask`/`todo`), `permission` (`read`/`list`/`edit`/`bash`/`web` — the `tool_permission` key that gates it), `path_arg` (which parameter is a filesystem path, for `external_directory` scope checks), `key_arg` (which argument to show in status/confirm labels, and for the future activity-lines glyph system)

### Machine Access & Permissions
- `ToolPolicy` (`tools/policy.py`) is the single permission resolution point; the loop and `/tool` both route through it — never special-case tool names for permission logic
- Actions: `allow` (no prompt), `ask` (y/N confirm in the loop via `_confirm_tool`), `deny` (tool filtered from the provider schema and refused on direct calls)
- Precedence: name-level `deny` / allow-whitelist → category action from `tool_permission` → `external_directory` escalation (read/write/list outside the project worktree becomes `ask`)
- `bash: ask` by default — every `run_command` confirms; set `tool_permission.bash = "allow"` to disable prompting
- Confirm prompts and tool status are ephemeral REPL UI — never persisted to session files
- Sandboxed exec (namespace/container isolation) and per-agent permission profiles are planned future work (see TODO)

### Adding a Provider
1. Create `src/replio/providers/<name>.py`
2. Subclass `BaseProvider`, implement the `chat()` event generator and `list_models()`
3. Add import + mapping in `chat.py` `_reinit_provider()` method
4. Add to `/connect` prompt flow if needed

### Adding a Slash Command
1. Open `commands/builtins.py`
2. Use `@registry.register('name', aliases=['a1', 'a2'])` decorator
3. Handler receives one string argument (the text after the command name)
4. If the command performs a tool action, call `chat_loop._tool_registry.execute(name, args)` rather than reimplementing it

### Future: Plugins
Tools and providers are planned to become installable plugins (roadmap Phase 5) via directory-based loading from `~/.config/replio/plugins/` and `.replio/plugins/` — plain Python modules that register into the existing registries, keeping the core lean and flexible.

## Roadmap

- **Phase 0** — Unified streaming agent loop (single SSE stream, `tool_calls` events)
- **Phase 1** — Unified dispatch (slash commands → same `ToolRegistry`, generic refinement)
- **Phase 2** — Machine access (read/write/exec tools, tool policies, `confirm`-gated exec)
- **Phase 3** — Personas (`/agent` with per-agent prompt, sessions, model)
- **Phase 4** — Delegation (`delegate` tool → sub-agent loops; team orchestration)
- **Phase 5** — Plugins (tools + providers installable, directory-based)

Implement one phase at a time. Docs-first: restructure planning docs, then build the phase, mark it `[x]`, and log it in `CHANGELOG.md`.

## Config Schema

```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "base_url": "https://api.ollama.com",
  "api_key": "",
  "temperature": 0.7,
  "max_tokens": 2048,
  "system_prompt": "",
  "tool_calling": true,
  "web_search": false,
  "search_results": 5,
  "tools.allow": [],
  "tools.deny": [],
  "tool_permission": {
    "read": "allow",
    "list": "allow",
    "edit": "allow",
    "bash": "ask",
    "web": "allow"
  }
}
```

## Testing

- Tests live in `tests/` and use stdlib `unittest` (no external test runner needed)
- **Mock tests** patch provider responses — no internet, no API key required
- Run all tests:
  ```bash
  python -m unittest discover tests
  ```
- Run a specific test file:
  ```bash
  python -m unittest tests.test_tool_calling
  ```
- Run before committing changes to verify core logic isn't broken
- Manual live tests (against real API) are done ad-hoc; not automated

## Session JSON Format

```json
{
  "name": "20250727_120000",
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-07-27T14:30:00+00:00"},
    {"role": "assistant", "content": "Hi! How can I help?", "timestamp": "2026-07-27T14:30:05+00:00", "duration": 4.8, "model": "llama3.2", "provider": "ollama"},
    {"role": "command", "content": "/model llama3.3", "timestamp": "2026-07-27T14:35:00+00:00"},
    {"role": "user", "content": "Now?", "timestamp": "2026-07-27T14:35:10+00:00"},
    {"role": "assistant", "content": "Ready.", "timestamp": "2026-07-27T14:35:15+00:00", "duration": 3.1, "model": "llama3.3", "provider": "ollama"}
  ]
}

## Tool Call Messages

```json
{"role": "assistant", "tool_calls": [{"id": "call_xxx", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"latest Python\"}"}}], "timestamp": "..."},
{"role": "tool", "tool_call_id": "call_xxx", "content": "Web search results...", "timestamp": "..."},
}
```
