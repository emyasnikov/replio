# TODO

## Phase 1 — Core Chat (done)
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

## Phase 2 — Polish
- [ ] `AGENTS.md` / `README.md` / `TODO.md` updates
- [ ] Error handling improvements (network timeout, auth errors)
- [ ] Thinking/reasoning token detection and dimmed display
- [ ] Markdown-aware streaming (basic formatting)
- [ ] Auto-session naming with first user message as context hint

## Phase 3 — Web Search
- [ ] Web search provider abstraction
- [ ] Default web search implementation (DuckDuckGo / custom API)
- [ ] `/search` command or inline `?` prefix
- [ ] Compact summary display with expandable details toggle

## Phase 4 — Sessions & Providers
- [ ] Session export to Markdown
- [ ] Session import from Markdown/JSON
- [ ] Groq provider
- [ ] OpenAI provider
- [ ] Anthropic provider (via OpenAI-compatible /messages endpoint)
- [ ] Provider auto-detection from base_url

## Phase 5 — Advanced
- [ ] Multi-line input (detect `"""` or `'''` blocks)
- [ ] `/compact` session summarization
- [ ] Config validation (test connection on change)
- [ ] Custom system prompts per session
- [ ] Streaming with thinking/reasoning block toggle
