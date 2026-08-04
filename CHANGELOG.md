# Changelog

## v0.7.0 — 2026-08-03

### Added

- Command registration metadata — `description` and `subcommands` on `CommandRegistry.register()` (`self.meta`); canonical names tracked so aliases can't shadow real command names
- Machine access tools (`tools/machine.py`): `read_file` (numbered lines, `offset`/`limit`, truncation), `list_dir` (sorted entries, dir markers, sizes), `write_file` (parent-dir creation, write/append), `run_command` (subprocess exec with timeout, stdout/stderr capture, exit code, 8k output cap)
- Tool permission model (`tools/policy.py`) — `ToolPolicy` resolves each tool call to `allow`/`ask`/`deny` from configurable permission keys (`tool_permission`: `read`/`list`/`edit`/`bash`/`web`) plus name-level `tools.allow`/`tools.deny` (deny and allow-whitelist take precedence)
- Path-scoped confirmation — read/write/list calls targeting paths outside the project worktree escalate to `ask` (opencode-style `external_directory`), so in-worktree file ops run unattended while external access prompts
- Confirm prompts in the agent loop (`_confirm_tool`) — `bash: ask` by default so every `run_command` confirms; cancelled calls feed `[cancelled]` tool results back to the model; denied tools are filtered from the provider schema entirely
- Registration metadata — `category`, `permission`, `path_arg`, `key_arg` on `ToolRegistry.register()` plus `permission_for()`/`path_arg_for()`/`key_arg_for()`/`schema_filtered()`; retrofitted `web_search`/`fetch_page` (forward-compat for the deferred activity-lines glyph system)
- `tests/test_tool_policy.py` (allow/deny, permission keys, external-directory escalation, precedence) and `tests/test_machine_tools.py` (read/list/write/exec against a temp dir, timeout, metadata)
- `/tool` policy tests — deny rejection, `ask` accept/decline, schema filtering of denied tools

### Changed

- `/help` compacts to one line per command with aliases inline (`/help, /h`) and subcommand rows beneath (`/session` → `new`/`list`/`load`/`delete`/`save`), all aligned to a computed description column
- `/session` (no args) reuses the shared subcommand metadata instead of a hardcoded usage block
- `/tool` command respects tool policy — listing shows only allowed tools, execution routes through `_run_tool()` (deny rejection + confirm prompts)
- `Session.to_dict()` and the agent loop unchanged — confirm prompts and tool status remain ephemeral REPL UI, never persisted

### Docs

- `TODO.md` Machine Access section expanded; sandboxed exec and per-agent permission profiles documented as later work
- `AGENTS.md` config schema + project structure updated with the permission model and new modules

## v0.6.0 - 2026-08-02

### Added

- `/tool <name> <json-args>` slash command — generic thin wrapper executing any registered tool via the same `ToolRegistry` the model uses; no args lists registered tools
- `tests/test_tool_registry.py` — registry metadata tests: `refine_required()` for `web_search` vs `fetch_page`/unknown
- `tests/test_commands.py` — `/tool` dispatch tests: registry execution, name listing, disabled path, invalid JSON
- Unified streaming agent loop (`_agent_loop()` in `chat.py`) — a single SSE stream per turn replaces the two-phase non-streaming decision + streaming call; `tool_calls` events are handled mid-stream, eliminating the double-call cost when no tools are used
- `_StreamRenderer` in `chat.py` — stateful streaming display (thinking markers, markdown, `<<<` prefix) extracted from the old `_stream_response` and reused across loop rounds
- `OllamaProvider.chat()` now accepts `tools`, forwards them in the stream payload, and accumulates fragmented `delta.tool_calls` into a `tool_calls` event
- `tests/helpers.py` — shared `make_chat()` builder for ChatLoop tests
- `tests/test_agent_loop.py` — loop-level tests: no-tools single round trip, thinking excluded from persisted content, error bail, empty stream
- `tests/test_ollama_provider.py` — provider streaming tests: fragmented tool-call accumulation, `done`/`thinking` events, `tools` in payload, error passthrough

### Changed

- `ToolRegistry.register()` accepts `refine` metadata; `refine_required()` lookup added — `web_search` registered with `refine=True`, and `_execute_tool_calls()` now refines via metadata instead of special-casing the `web_search` name
- `BaseProvider.chat()` signature gains `tools: list[dict] | None = None`
- `_handle_message()` branches collapse onto `_agent_loop()`; `chat_nonstreaming()` is now used only by `_refine_query()`
- `tests/test_tool_calling.py` rewritten against the streaming event generator

### Removed

- `_chat_with_tools()`, `_stream_response()`, `_output_content()` and `_response_start` from `chat.py`
- `/search` and `/web` slash commands — model tool-calling and `web_search` auto mode cover searching

## v0.5.0 — 2026-07-28

### Added

- `_TextExtractor` class in `tools/builtins.py` — stdlib HTMLParser-based text extraction for `fetch_page`
- Test `test_empty_stream_falls_back_to_nonstreaming_content` — verifies fallback saves non-streaming content when streaming returns empty

### Changed

- `Session.to_dict()` filters out `role: tool` messages — session files only contain REPL-visible messages (user, assistant, command, system)

### Fixed

- Final assistant response missing from session when streaming returned no tokens — fall back to non-streaming result content when `_stream_response()` returns empty
- `fetch_page` returned raw HTML/JS/CSS noise — replaced regex tag-stripping with `_TextExtractor` (HTMLParser) that drops `<script>`, `<style>`, `<svg>`, `<noscript>` and extracts clean visible text
- Session files stored raw tool-result content that was never displayed in the REPL — filtered `role: tool` messages from serialized output; assistant `tool_calls` (web_search, fetch_page declarations) still documented

## v0.4.0 — 2026-07-28

### Added

- 3 new test cases: empty-content, multiple tool calls, and API error path (now 7 tests total)

### Fixed

- Tool-call messages (assistant tool_calls + tool results) lost when streaming produced empty content or an exception occurred — wrapped `_chat_with_tools()` and `_stream_response()` in `try/finally` so session is always persisted
- `_chat_with_tools()` no longer skips `_stream_response()` when `chat_nonstreaming` returns empty/null content — final response is always streamed
- Session file rename left JSON `name` field stale — added `session_auto_save()` after rename so the file always has the correct session name

## v0.3.0 — 2026-07-28

### Added

- Auto-session naming: first user message auto-names the session (sanitized, truncated to 40 chars). Renames the `.json` file on disk
- Markdown-aware streaming: code blocks in cyan, inline code in green, bold text rendered with ANSI bold. Disabled by default (`markdown_streaming: false`). Enable via config.
- Thinking/reasoning token detection: provider-level `reasoning_content` field (DeepSeek R1, o1, o3). Configurable via `show_thinking` (default `true`)
- Error handling: `_post()`, `chat_nonstreaming()`, `chat()`, `_chat_with_tools()`, and `list_models()` now catch `HTTPError` (auth 401, server 500) and `URLError` (network, timeout) gracefully — errors print in red, REPL continues
- `_chat_with_tools()`: when no tools are used, now calls `_stream_response()` for live token output instead of dumping the full response at once
- `query_refine` config system: when enabled, short web_search queries (≤ `query_refine_min_words` words) are auto-refined via a lightweight model call with `query_refine_context` recent messages as context. Configurable via `query_refine`, `query_refine_min_words` (default 3), `query_refine_context` (default 4)
- `tool_status_visible` config option (default `true`): when `false`, hides dimmed `[tool: args]` status lines during tool execution
- Mock test suite for tool calling (`tests/test_tool_calling.py`): 4 offline tests covering no-tools, single-tool, unknown-tool error, and force-search paths

### Fixed

- Markdown streaming now off by default; the state machine was unreliable on real streaming output
- Removed `...` as thinking marker/closer (too many false positives in normal text)

## v0.2.0 — 2026-07-27

### Added

- Auto-search mode: set `web_search: true` in config to search on every message
- Search results displayed as compact list, injected as AI context for grounded responses
- `/search <query>` and `/web <query>` commands
- `web/display.py` — `format_results()` for terminal, `format_context()` for AI context injection
- `web/search.py` — `DDGResultParser` (HTMLParser), search endpoint at `lite.duckduckgo.com`
- Web search: DuckDuckGo Lite via `html.parser` — `/search <query>` and `/web <query>` commands
- Config default: `tool_calling: true`
- `/search` command integrated with tool calling (uses `_chat_with_tools(force_search=...)`)
- `_show_tool_status()` — dimmed `[web_search: "query"]` status during tool execution
- `_chat_with_tools()` — decision loop that executes tool calls and injects results
- Ollama provider: refactored payload generation, `chat_nonstreaming()` with `tools` support
- `BaseProvider.chat_nonstreaming()` — returns `{role, content, tool_calls, finish_reason}`
- `tools/builtins.py` — `web_search` and `fetch_page` tools
- `tools/registry.py` — decorator-based tool registration (OpenAI function calling format)
- Tool calling system: two-phase chat (non-streaming tool decision → stream final content)

## v0.1.0 — 2026-07-27

### Added

- `<<< ` prefix on streaming responses for clear user/AI separation
- Command logging: all slash commands stored as `command`-role messages in session history
- Model tracking: per-message `model` + `provider` on each assistant response
- Elapsed time display after each response
- Timestamps on every message and duration tracking on assistant responses
- Streaming token display with ANSI-colored prompt
- REPL loop with readline input history and tab completion
- Built-in slash commands: `/help`, `/connect`, `/model`, `/provider`, `/session`, `/config`, `/exit`
- Command registry with decorator-based registration
- Session manager: create, list, load, delete, auto-save (JSON format)
- Ollama cloud provider (defaults to `https://api.ollama.com`)
- Provider abstraction layer (OpenAI-compatible `/v1/chat/completions`)
- HTTP SSE streaming via urllib for live token output
- Config module: global + local JSON merge (`~/.config/replio/` + `.replio/`)
- Project scaffold (pyproject.toml, .venv, directory structure)
