# TODO

## Ideas

- [ ] Citations / source attribution — return URL + snippet with every answer
- [ ] Bookmarks — `/bookmark add/remove/list` for session pinning
- [ ] Interactive data analysis — CSV querying, SQL execution, code eval in REPL
- [ ] Notebook mode — persistent editable cells with run outputs
- [ ] Hybrid web + local RAG — vector store (FAISS/Weaviate), embeddings, local document search
- [ ] Command palette / fuzzy search — CTRL-P style history search
- [ ] Topic-aware ranking — classifier for query intent to weight search results

## Polish

- [ ] Custom system prompts per session
- [ ] Config validation (test connection on change)
- [ ] `/compact` session summarization
- [ ] Multi-line input (detect `"""` or `'''` blocks)

---

## Agentic Core

- [x] Unified streaming agent loop
  - [x] Single SSE stream, detect `tool_calls` vs content from the first delta
  - [x] Eliminates double-call cost when no tools are used
- [ ] Unified dispatch
  - [ ] Slash commands call the same `ToolRegistry` as the model
  - [ ] Generic query refinement via tool metadata; collapse `_handle_message` branches

## Machine Access

- [ ] `read_file`, `write_file`, `list_dir`, `run_command` tools
- [ ] `tools.allow` / `tools.deny` config policies
- [ ] `confirm`-gated destructive/exec tools

## Personas & Delegation

- [ ] `/agent` personas — per-agent system prompt, session namespace, optional model override
- [ ] `delegate(persona, task)` tool → sub-agent loop returning a result
- [ ] PM/dev/tester team orchestration as a user-facing pattern

## Plugins

- [ ] Directory-based plugin loading (`.replio/plugins/`, `~/.config/replio/plugins/`)
- [ ] Tools as installable plugins
- [ ] Providers as installable plugins
- [ ] Plugin manifest + docs

## Providers

- [ ] OpenAI provider
- [ ] Groq provider
- [ ] Anthropic provider (via OpenAI-compatible /messages endpoint)
- [ ] Provider auto-detection from base_url
- [x] Base provider (OpenAI-compatible interface)
- [x] Ollama cloud provider

## Sessions & Import/Export

- [ ] Session export to Markdown
- [ ] Session import from Markdown/JSON
- [x] Session manager (JSON CRUD)
- [x] Session save after file rename — JSON `name` field matches filename
- [x] Auto-session naming with first user message as context hint
- [x] Tool-result content in session files — filtered from serialization; assistant `tool_calls` preserved

## Web Search

- [x] DuckDuckGo Lite search via `html.parser` (`web/search.py`)
- [x] Terminal + AI context formatting (`web/display.py`)
- [x] `/search <query>` and `/web <query>` commands
- [x] Auto-search mode (`web_search: true` config)
- [x] `fetch_page` returns HTML/JS noise — `_TextExtractor` (HTMLParser) for clean text extraction
- [x] Search term extraction — `query_refine` config: auto-refines short web_search queries via a lightweight model call, injecting recent conversation context

## Tool Calling

- [x] `tools/registry.py` — decorator-based tool registration
- [x] `tools/builtins.py` — `web_search` and `fetch_page` tools
- [x] `BaseProvider.chat_nonstreaming()` — non-streaming tool decision round
- [x] Two-phase chat: non-streaming tool decision → stream final content
- [x] `_show_tool_status()` — dimmed status during tool execution
- [x] `/search` command integration with tool calling
- [x] Config default: `tool_calling: true`
- [x] Add `tool_status_visible` config flag (default `true`)
- [x] Verify tool calling integration end-to-end

## Streaming

- [ ] Word-level streaming buffering: avoid mid-word breaks by buffering tokens until a space character
- [ ] Streaming with thinking/reasoning block toggle
- [x] Thinking/reasoning token detection and dimmed display
- [x] Markdown-aware streaming (basic formatting, disabled by default via `markdown_streaming` config)
- [x] Error handling improvements (network timeout, auth errors)
- [x] Edge cases: streaming when `tool_calling=true` but no tools used
- [x] Tool-call messages lost on exception — `try/finally` in `_chat_with_tools` and `_stream_response`
- [x] Final assistant response missing when streaming returns empty — fallback to non-streaming content

## REPL & Core

- [x] Project scaffolding (pyproject.toml, venv, dir structure)
- [x] Config module (global + local JSON merge)
- [x] HTTP SSE streaming utility (urllib)
- [x] REPL loop with readline history + tab completion
- [x] Command registry + built-in slash commands
- [x] Streaming token display
- [x] Documentation (README, AGENTS.md, TODO.md, CHANGELOG.md)
