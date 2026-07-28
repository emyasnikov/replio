# TODO

## Core Chat
- [x] Project scaffolding (pyproject.toml, venv, dir structure)
- [x] Config module (global + local JSON merge)
- [x] HTTP SSE streaming utility (urllib)
- [x] Base provider (OpenAI-compatible interface)
- [x] Ollama cloud provider
- [x] Session manager (JSON CRUD)
- [x] Command registry + built-in slash commands
- [x] REPL loop with readline history + tab completion
- [x] Streaming token display
- [x] Documentation (README, AGENTS.md, TODO.md, CHANGELOG.md)

## Tool Calling
- [x] `tools/registry.py` — decorator-based tool registration
- [x] `tools/builtins.py` — `web_search` and `fetch_page` tools
- [x] `BaseProvider.chat_nonstreaming()` — non-streaming tool decision round
- [x] Two-phase chat: non-streaming tool decision → stream final content
- [x] `_show_tool_status()` — dimmed status during tool execution
- [x] `/search` command integration with tool calling
- [x] Config default: `tool_calling: true`

## Web Search
- [x] DuckDuckGo Lite search via `html.parser` (`web/search.py`)
- [x] Terminal + AI context formatting (`web/display.py`)
- [x] `/search <query>` and `/web <query>` commands
- [x] Auto-search mode (`web_search: true` config)

## Polish
- [x] Verify tool calling integration end-to-end
- [x] Add `tool_status_visible` config flag (default `true`)
- [x] Search term extraction — `query_refine` config: auto-refines short web_search queries via a lightweight model call, injecting recent conversation context
- [x] Edge cases: streaming when `tool_calling=true` but no tools used
- [x] Error handling improvements (network timeout, auth errors)
- [x] Thinking/reasoning token detection and dimmed display
- [x] Markdown-aware streaming (basic formatting, disabled by default via `markdown_streaming` config)
- [x] Auto-session naming with first user message as context hint

## Sessions & Providers
- [ ] Session export to Markdown
- [ ] Session import from Markdown/JSON
- [ ] Groq provider
- [ ] OpenAI provider
- [ ] Anthropic provider (via OpenAI-compatible /messages endpoint)
- [ ] Provider auto-detection from base_url

## Future Optimizations
- [ ] Unified streaming: rewrite `_chat_with_tools()` to use a single SSE stream, detecting tool_calls vs content from the first delta. Eliminates double-call cost when no tools are used.
- [ ] Word-level streaming buffering: avoid mid-word breaks by buffering tokens until a space character

## Advanced
- [ ] Multi-line input (detect `"""` or `'''` blocks)
- [ ] `/compact` session summarization
- [ ] Config validation (test connection on change)
- [ ] Custom system prompts per session
- [ ] Streaming with thinking/reasoning block toggle
