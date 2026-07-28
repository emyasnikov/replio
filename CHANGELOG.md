# Changelog

## 2026-07-27

### Added
- Tool calling system: two-phase chat (non-streaming tool decision → stream final content)
- `tools/registry.py` — decorator-based tool registration (OpenAI function calling format)
- `tools/builtins.py` — `web_search` and `fetch_page` tools
- `BaseProvider.chat_nonstreaming()` — returns `{role, content, tool_calls, finish_reason}`
- Ollama provider: refactored payload generation, `chat_nonstreaming()` with `tools` support
- `_chat_with_tools()` — decision loop that executes tool calls and injects results
- `_show_tool_status()` — dimmed `[web_search: "query"]` status during tool execution
- `/search` command integrated with tool calling (uses `_chat_with_tools(force_search=...)`)
- Config default: `tool_calling: true`
- Web search: DuckDuckGo Lite via `html.parser` — `/search <query>` and `/web <query>` commands
- Auto-search mode: set `web_search: true` in config to search on every message
- Search results displayed as compact list, injected as AI context for grounded responses
- `web/search.py` — `DDGResultParser` (HTMLParser), search endpoint at `lite.duckduckgo.com`
- `web/display.py` — `format_results()` for terminal, `format_context()` for AI context injection
- Project scaffold (pyproject.toml, .venv, directory structure)
- Config module: global + local JSON merge (`~/.config/replio/` + `.replio/`)
- HTTP SSE streaming via urllib for live token output
- Provider abstraction layer (OpenAI-compatible `/v1/chat/completions`)
- Ollama cloud provider (defaults to `https://api.ollama.com`)
- Session manager: create, list, load, delete, auto-save (JSON format)
- Command registry with decorator-based registration
- Built-in slash commands: `/help`, `/connect`, `/model`, `/provider`, `/session`, `/config`, `/exit`
- REPL loop with readline input history and tab completion
- Streaming token display with ANSI-colored prompt
- Timestamps on every message and duration tracking on assistant responses
- Elapsed time display after each response
- Model tracking: per-message `model` + `provider` on each assistant response
- Command logging: all slash commands stored as `command`-role messages in session history
- `<<< ` prefix on streaming responses for clear user/AI separation

### Fixed
- `ollama.py` streaming crash: `KeyError: 'type'` on raw SSE events without `'type'` key

### Documentation
- README.md, AGENTS.md, TODO.md, CHANGELOG.md

## 2026-07-28

### Added
- Mock test suite for tool calling (`tests/test_tool_calling.py`): 4 offline tests covering no-tools, single-tool, unknown-tool error, and force-search paths
- `tool_status_visible` config option (default `true`): when `false`, hides dimmed `[tool: args]` status lines during tool execution
