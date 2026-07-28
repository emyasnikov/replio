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
- `query_refine` config system: when enabled, short web_search queries (≤ `query_refine_min_words` words) are auto-refined via a lightweight model call with `query_refine_context` recent messages as context. Configurable via `query_refine`, `query_refine_min_words` (default 3), `query_refine_context` (default 4)
- `_chat_with_tools()`: when no tools are used, now calls `_stream_response()` for live token output instead of dumping the full response at once
- Error handling: `_post()`, `chat_nonstreaming()`, `chat()`, `_chat_with_tools()`, and `list_models()` now catch `HTTPError` (auth 401, server 500) and `URLError` (network, timeout) gracefully — errors print in red, REPL continues
- Thinking/reasoning token detection: provider-level `reasoning_content` field (DeepSeek R1, o1, o3). Configurable via `show_thinking` (default `true`)
- Markdown-aware streaming: code blocks in cyan, inline code in green, bold text rendered with ANSI bold. Disabled by default (`markdown_streaming: false`). Enable via config.
- Auto-session naming: first user message auto-names the session (sanitized, truncated to 40 chars). Renames the `.json` file on disk

### Fixed
- Removed `...` as thinking marker (too many false positives in normal text)
- Removed `...` as thinking closer (same issue)
- Markdown streaming now off by default; the state machine was unreliable on real streaming output
- `_chat_with_tools()` no longer skips `_stream_response()` when `chat_nonstreaming` returns empty/null content — final response is always streamed
- Added 3 new test cases: empty-content, multiple tool calls, and API error path (now 7 tests total)
- Session file rename left JSON `name` field stale — added `session_auto_save()` after rename so the file always has the correct session name
- Tool-call messages (assistant tool_calls + tool results) lost when streaming produced empty content or an exception occurred — wrapped `_chat_with_tools()` and `_stream_response()` in `try/finally` so session is always persisted
- Final assistant response missing from session when streaming returned no tokens — fall back to non-streaming result content when `_stream_response()` returns empty
- `fetch_page` returned raw HTML/JS/CSS noise — replaced regex tag-stripping with `_TextExtractor` (HTMLParser) that drops `<script>`, `<style>`, `<svg>`, `<noscript>` and extracts clean visible text
- Session files stored raw tool-result content that was never displayed in the REPL — filtered `role: tool` messages from serialized output; assistant `tool_calls` (web_search, fetch_page declarations) still documented

### Added
- `_TextExtractor` class in `tools/builtins.py` — stdlib HTMLParser-based text extraction for `fetch_page`
- Test `test_empty_stream_falls_back_to_nonstreaming_content` — verifies fallback saves non-streaming content when streaming returns empty

### Changed
- `Session.to_dict()` filters out `role: tool` messages — session files only contain REPL-visible messages (user, assistant, command, system)
