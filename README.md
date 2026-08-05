# REPL.io

<p>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python >=3.10">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
</p>

A zero-dependency AI chat REPL for your terminal.

## Why?

REPL.io uses **nothing but the Python standard library**.
No dependencies and gigabytes of `node_modules`.
Clone and run.

## Features

- **Zero external dependencies** — Python stdlib only
- **Multi-provider** — Ollama, OpenAI, Anthropic, Groq, any OpenAI-compatible API
- **Streaming responses** — live token-by-token output via SSE
- **Web search** — DuckDuckGo integration, page fetching, auto-query refinement
- **Tool calling** — models search the web and fetch pages on the fly
- **Machine access** — read, list, write, and run shell commands, gated by path-scoped permission prompts
- **Sessions** — save, load, switch, and auto-name conversations
- **Slash commands** — `/help`, `/model`, `/provider`, `/connect`, `/session`, `/config`, `/exit`
- **Dual config** — global `~/.config/replio/` + per-project `.replio/` JSON merge
- **Input history** — readline-based up/down recall + tab completion
- **Thinking/reasoning display** — see model reasoning tokens (DeepSeek R1, o1, etc.)

## Quick Start

```bash
pip install replio
replio
```

Or from source:

```bash
git clone https://github.com/emyasnikov/replio && cd replio
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/replio
```

### First-time setup

```
>>> /connect
  Provider [ollama]:
  Base URL [https://ollama.com]:
  API key: sk-...
  Model [gpt-oss:20b-cloud]:
```

## Usage

```
>>> /help            list all commands
>>> /model <model>   switch model
>>> /tool <name> <json>  run a tool directly
>>> /session list    saved conversations
>>> /exit            goodbye
```

Type any message to chat. Tab-complete `/` commands. Arrow keys for history.

## Machine Access & Permissions

The model can read and search your machine (`read_file`, `list_dir`, `glob`, `grep`), write (`write_file`), and execute shell commands (`run_command`). Access is governed by a permission policy:

```json
{
  "tools.deny": [],
  "tools.allow": [],
  "tool_permission": {
    "read": "allow",
    "list": "allow",
    "edit": "allow",
    "bash": "ask",
    "web": "allow"
  }
}
```

- `allow` — runs without prompting; `ask` — prompts y/N; `deny` — disabled (also hidden from the model).
- `tools.deny` / `tools.allow` — exact tool-name policies (`deny` and allow-whitelist take precedence).
- Reads/writes/lists **outside the project directory** always prompt for confirmation, even when the category is `allow`.
- `bash` is `ask` by default — every shell command is confirmed. Set `"bash": "allow"` to skip prompting.

Confirm prompts and tool status are ephemeral UI and are never written to session files.

## Sessions

Sessions are complete logs: every message, tool call + result, reasoning (`thinking` metadata), and error is persisted. `errors` holds failed provider requests, and `created_at`/`updated_at` track the session lifetime.

- `session_tool_max_chars` (default `0` = unlimited) caps how much of each tool result is written to disk — the in-memory context always keeps the full result.
- `tool_analysis` (default `false`) stores a model-generated one-line insight summary on each tool result, so a log can be reconstructed without re-running the tool.

## Project Structure

```
src/replio/
├── chat.py           REPL loop + streaming display
├── config.py         Config load/merge/save
├── commands/         Slash command system
├── providers/        LLM provider abstraction
├── sessions/         Session CRUD
├── tools/            Web search, page fetch, tool registry
├── web/              DuckDuckGo search + formatting
└── utils/            HTTP SSE streaming
```

## Adding a Provider

Create a subclass of `BaseProvider` implementing `chat()` and `list_models()` using the OpenAI-compatible `/v1/chat/completions` format, then register it in `ChatLoop._reinit_provider()`.

## Contributing

See [TODO.md](TODO.md) for open tasks and [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT
