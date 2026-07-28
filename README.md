# REPL.io

A terminal-based REPL AI chat application supporting multiple LLM providers. Inspired by OpenCode and Open WebUI.

Zero external dependencies — Python stdlib only.

## Features

- **Multi-provider chat** — Ollama (local/cloud), Groq, OpenAI, Anthropic (OpenAI-compatible interface)
- **Session management** — create, switch, export/import sessions saved as JSON
- **Streaming responses** — live token-by-token output with SSE
- **Web search integration** — compact summary with expandable details (planned)
- **Slash commands** — `/help`, `/model`, `/provider`, `/connect`, `/session`, `/config`, `/exit`
- **Configurable** — global `~/.config/replio/config.json` + local `.replio/config.json` merge
- **Input history** — readline-based up/down recall + tab completion for commands

## Features Status

| Feature | Status | Notes |
|---------|--------|-------|
| Web search (DuckDuckGo) | ✅ Done | `web_search` tool + `/search` command |
| Page fetching | ✅ Done | `fetch_page` tool, HTML→text, 8K truncation |
| Query refinement | ✅ Done | `query_refine` config, auto-improves short queries |
| Tool calling (two-phase) | ✅ Done | Model decides to search/fetch via function calling |
| Thinking/reasoning display | ✅ Done | `show_thinking` config, provider `reasoning_content` |
| Markdown-aware streaming | ✅ Done | `markdown_streaming` config (opt-in, off by default) |
| Session management | ✅ Done | Create, list, load, delete, auto-save, auto-naming |
| Slash commands | ✅ Done | `/help`, `/model`, `/provider`, `/connect`, `/session`, `/config`, `/exit` |
| Input history + tab complete | ✅ Done | readline-based |
| Error handling (network, auth) | ✅ Done | Graceful red error messages, REPL continues |
| Citations / source attribution | ❌ Planned | Return URL + snippet with every answer |
| Bookmarks (session pinning) | ❌ Planned | `bookmark add/remove/list` commands |
| Interactive data analysis | ❌ Planned | CSV querying, SQL, code execution in REPL |
| Notebook mode (cells) | ❌ Planned | Persistent editable cells with outputs |
| Hybrid web + local RAG | ❌ Future | Vector store (FAISS/Weaviate), breaks stdlib-only |
| Command palette / fuzzy search | ❌ Future | Requires `prompt_toolkit` or `fzf`, breaks stdlib-only |
| Topic-aware ranking | ❌ Future | ML classifier for query intent tagging |

## Quick Start

```bash
git clone <repo> && cd repl.io
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/replio
```

### First-time setup

```
>>> /connect
  Provider [ollama]:
  Base URL [https://api.ollama.com]:
  API key (leave empty to skip): sk-...
  Model [llama3.2]:
```

## Usage

```
>>> /help            list all commands
>>> /model <name>    switch model
>>> /provider <name> switch provider
>>> /connect         interactive provider setup
>>> /config <k> <v>  set config value
>>> /session new     start new session
>>> /session list    list saved sessions
>>> /session load n  load a session
>>> /exit            quit
```

Type any message to chat. Tab-complete `/` commands. Up/down arrows for history.

## Project Structure

```
src/replio/
├── main.py           CLI entry point
├── config.py         Config load/merge/save
├── chat.py           REPL loop + streaming display
├── providers/
│   ├── base.py       Abstract provider (OpenAI-compatible)
│   └── ollama.py     Ollama implementation
├── sessions/
│   └── manager.py    Session CRUD
├── commands/
│   ├── registry.py   Command registration
│   └── builtins.py   Built-in slash commands
└── utils/
    └── http.py       urllib-based SSE streaming
```

## Adding a Provider

Create a subclass of `BaseProvider` implementing `chat()` and `list_models()` using the OpenAI-compatible `/v1/chat/completions` format, then register it in `ChatLoop._reinit_provider()`.
