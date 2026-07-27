# REPL.ai — Agent Guide

## Project

A terminal-based REPL AI chat app with multi-provider support, sessions, web search, and slash commands.

## Tech Stack

- Python >=3.10, **stdlib only** (no external dependencies)
- `readline` — input history + tab completion for slash commands
- `urllib.request` — HTTP + SSE streaming
- `urllib.error` — HTTP error handling
- `json` / `pathlib` / `os` — config and session storage

## Project Structure

```
repl.ai/
├── pyproject.toml
├── AGENTS.md
├── README.md
├── TODO.md
├── CHANGELOG.md
├── src/replai/
│   ├── __init__.py
│   ├── __main__.py          # python -m replai
│   ├── main.py              # CLI arg parsing + bootstrap
│   ├── config.py            # JSON config (global + local merge)
│   ├── chat.py              # Main REPL loop with readline
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
│   │   └── builtins.py      # /help, /connect, /model, /search, etc.
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
- `BaseProvider` uses OpenAI-compatible `/v1/chat/completions` format
- Adding a provider = subclass `BaseProvider` + register in `ChatLoop._reinit_provider()`
- Config: global (`~/.config/replai/config.json`) → local (`.replai/config.json`) merge, local wins
- Sessions stored as `.replai/sessions/<name>.json`
- Slash commands registered via `@registry.register()` decorator

### Adding a Provider
1. Create `src/replai/providers/<name>.py`
2. Subclass `BaseProvider`, implement `chat()` and `list_models()`
3. Add import + mapping in `chat.py` `_reinit_provider()` method
4. Add to `/connect` prompt flow if needed

### Adding a Slash Command
1. Open `commands/builtins.py`
2. Use `@registry.register('name', aliases=['a1', 'a2'])` decorator
3. Handler receives one string argument (the text after the command name)

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
  "web_search": false,
  "search_results": 5
}
```

## Changelog Convention

`CHANGELOG.md` is grouped by **days** (not versions). Entries under `## YYYY-MM-DD` headings.

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
```
