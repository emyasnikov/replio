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

1. **Agent loop** (`engine.py`) — the headless core. Each turn runs a single streaming request. The provider's `chat()` is a generator yielding events, and the engine reacts:
   - `thinking` / `token` — streamed to the sink (`UISink`); `ReplUI` renders ANSI thinking + optional markdown, `HeadlessUI` logs to stderr / buffers for JSON
   - `tool_calls` — append the assistant message, execute each call, append `tool` results, then continue the loop
   - `error` — record + print and bail
   - `done` — persist the assistant message (timestamp/duration/model) and stop
   
   One stream, one round trip when no tools are used. `chat_nonstreaming()` is reserved for query refinement, not the main path. The loop is front-end agnostic: `ChatLoop` (REPL), `replio run` (CLI), and `replio serve` (HTTP) all call `Engine.chat(text) -> TurnResult`. The `<thinking>` marker split lives in the engine so thinking stays separate from content.

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
│   ├── main.py              # CLI arg parsing + bootstrap (default REPL, run, serve)
│   ├── cli.py               # `replio run` / `replio serve` headless entry points
│   ├── config.py            # JSON config (global + local merge)
│   ├── engine.py            # Headless agent core — Engine + TurnResult
│   ├── chat.py              # ChatLoop(Engine) — REPL shell with readline
│   ├── ui.py                # UISink — ReplUI / HeadlessUI / NullUI renderers
│   ├── server.py            # stdlib HTTP JSON API (POST /chat, GET /sessions, GET /health)
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
│   │   └── machine.py       # read_file, list_dir, write_file, run_command, glob, grep tools
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
- No external dependencies — stdlib only; plugins may opt into third-party deps via their manifest, the core never depends on them
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
- `TODO.md` has three zones. Ideas are plain bullets at the very top (no header, no checkbox — they evolve over time), followed by `## Open` (defined `[ ]` tasks) and `## Done` (`[x]` items, separated by `---`). Within `## Open` and `## Done`, items are sorted newest-first so new tasks are added at the top of their zone without reorganizing; nested sub-bullets are preserved (e.g. machine tools, tool policy). Completed items stay in `## Done` and are never moved to an archive.
- `CHANGELOG.md` is grouped by **versions**, newest at the top — new `## vX.Y.Z — YYYY-MM-DD` sections go above previous ones, so the latest changes are readable with `head`. Entries under each version form a **single flat bullet list, newest first** (no `### Added`/`### Changed`/`### Removed` grouping).
- After completing a planned task: mark it `[x]` in `TODO.md` and add entries under the current version section at the top of `CHANGELOG.md` (start a new version section first if none exists).
- Keep both files in sync with actual project state.
- Keep `version` in `pyproject.toml` in sync with the current version in `CHANGELOG.md` — bump it whenever a release section is started or finalized.

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
2. Subclass `OpenAICompatibleProvider`, set `DEFAULT_BASE_URL` / `DEFAULT_MODEL` (override `_headers()`/`_payload()` only for non-standard auth or bodies)
3. Add the class to the `PROVIDERS` dict in `providers/__init__.py`
4. Add a hostname match in `detect_provider()` so `/connect` auto-selects it

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
  "max_tokens": 0,
  "system_prompt": "",
  "tool_calling": true,
  "tool_analysis": false,
  "session_tool_max_chars": 0,
  "show_context_size": true,
  "clear_screen": true,
  "compact_keep": 4,
  "noise_tools": ["fetch_page"],
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

`max_tokens` defaults to `0` = unset (omitted from the provider payload, so the provider's own default applies). Set a positive value to re-enable a cap; hitting it prints a warning and logs a session `errors` entry.

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

Sessions are complete logs — every message, tool call + result, reasoning, and error is persisted, and entries are **never removed** (append-only; compaction only trims the provider context). `role: tool` messages are kept (with optional `session_tool_max_chars` truncation, and `noise_tools` results replaced by a marker, at serialization time only). `thinking` metadata holds reasoning before each tool call/answer and is excluded from `content`.

```json
{
  "name": "20250727_120000",
  "created_at": "2026-07-27T14:30:00+00:00",
  "updated_at": "2026-07-27T14:35:15+00:00",
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-07-27T14:30:00+00:00"},
    {"role": "assistant", "content": "Hi! How can I help?", "timestamp": "2026-07-27T14:30:05+00:00", "duration": 4.8, "model": "llama3.2", "provider": "ollama"},
    {"role": "command", "content": "/model llama3.3", "timestamp": "2026-07-27T14:35:00+00:00"},
    {"role": "user", "content": "Now?", "timestamp": "2026-07-27T14:35:10+00:00"},
    {"role": "assistant", "content": "Ready.", "timestamp": "2026-07-27T14:35:15+00:00", "duration": 3.1, "model": "llama3.3", "provider": "ollama", "thinking": "The user is switching models, just confirm."},
    {"role": "command", "content": "/compact", "timestamp": "...", "result": "Summary of the earlier conversation…", "compact_from": 8}
  ],
  "errors": [
    {"code": 401, "message": "Unauthorized", "timestamp": "2026-07-27T14:40:00+00:00"}
  ]
}
```

A `command` message with a `result` is a compaction record: `result` holds the summary, `compact_from` is the index into `messages` where the kept portion starts. `ChatLoop._provider_messages()` prepares the log for the API — `command` role messages are dropped (records become `system` summaries), dangling tool messages are skipped.

## Tool Call Messages

```json
{"role": "assistant", "tool_calls": [{"id": "call_xxx", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"latest Python\"}"}}], "timestamp": "...", "thinking": "..."},
{"role": "tool", "tool_call_id": "call_xxx", "content": "Web search results...", "timestamp": "...", "tool": "web_search", "analysis": "Pages about recent Python releases — 3.13 is the latest."},
```

`tool` messages carry the originating `tool` name (used to identify `noise_tools` at persistence time) and an optional `analysis` insight. The provider payload is prepared by `_provider_messages()` — `command` role messages are dropped, compaction records become `system` summaries, and dangling tool messages (e.g. at a `compact_from` boundary) are skipped.

