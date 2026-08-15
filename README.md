# REPL.io

<p>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python >=3.10">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
</p>

A lightweight, zero-dependency agentic tooling core with an interactive REPL chat.

## Why?

REPL.io uses **nothing but the Python standard library**.
No dependencies and gigabytes of `node_modules`.

## Features

- **Zero dependencies, honest footprint** — Just clone and run, nothing to install
- **Local-first & private** — Config and session logs live on your disk
- **One process, two ways** — Same agent core for terminal REPL and headless mode
- **Multi-provider by design** — Ollama, OpenAI, Anthropic etc.
- **Streaming responses** — Token-by-token output via SSE
- **Web search** — Auto web search, page fetching and query refinement
- **Machine access** — Read/write files and run shell commands
- **Sessions** — Full captured conversations, even on tool use
- **Compaction** — Summarize long conversations and trim the context

## Quick Start

```bash
pipx install replio
replio
```

Or from source:

```bash
git clone https://github.com/emyasnikov/replio.git && cd replio
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/replio
```

## Usage

### REPL

First-time setup using REPL:

```
>>> /connect
  Provider [ollama]:
  Base URL [https://ollama.com]:
  API key: ...
  Model [gpt-oss:20b-cloud]:
```

Type any message to chat. Tab-complete `/` commands and session names (e.g. `/session load <Tab>`, bash-style). Arrow keys for history.

```
>>> Hi
<<< Hello! How can I help you today?
>>> /exit
```

### CLI

Stream plain text with `--output text` or return the results as JSON, log tool status and diagnostics to stderr with `--verbose`, and address a persistent session with `--session-id <id>`. Tools that require confirmation are auto-denied in by default, just pass `--yes` to approve them.

```bash
replio run --prompt "Hi"
{
  "content": "Hello! How can I help you today?",
  "thinking": null,
  "tool_calls": [],
  "errors": [],
  "duration": 7.0,
  "usage": null,
  "model": "gpt-oss:20b-cloud",
  "provider": "ollama",
  "session": "20260814_192251_hi",
  "status": "ok"
}
```

### API

Server exposes different JSON endpoints like `POST /chat` (`{"prompt": ...}`, optionally `{"session_id": ...}`) returns the same turn result as the CLI, `GET /sessions` lists saved sessions.

```bash
replio serve
replio serve - http://127.0.0.1:8787 (POST /chat, GET /sessions, GET /health, GET /version)
[replio] "POST /chat HTTP/1.1" 200 -
```

```bash
curl localhost:8787/chat -X POST -d '{"prompt": "Hi"}'
{"content": "Hello! 👋 How can I help you today?", "thinking": null, "tool_calls": [], "errors": [], "duration": 7.0, "usage": null, "model": "gpt-oss:20b-cloud", "provider": "ollama", "session": "20260814_192711_hi", "status": "ok"}
```

## Machine Access & Permissions

The model can read and search your machine (`read_file`, `list_dir`, `glob`, `grep`), write (`write_file`), and execute shell commands (`run_command`). Access is governed by a permission policy.


## Sessions

Sessions are complete logs: every message, tool call + result, reasoning (`thinking` metadata), and error is persisted — entries are never removed, not even on compaction. `errors` holds failed provider requests, and `created_at`/`updated_at` track the session lifetime. Both headless modes run the same agent core and session store as the REPL, so conversations are interchangeable across all three.

## Roadmap

- **Headless core** — `replio run` (one-shot JSON in/out) and `replio serve` (stdlib HTTP API) over the same agent loop, for CI/CD, cron, and scripting
- **Coding toolchain** — `code_lint`/`code_format`/`code_test`/`code_debug`, `git`, `docs_search` tools and workspace sessions
- **Enterprise data** — ingestion, time-series analysis, model inference, optimization, and SCADA tools as plugins
- **Action & reporting** — reporting/email push, audit logging, metrics, onboarding wizard

Open tasks and details live in [TODO.md](TODO.md).

## Contributing

See [TODO.md](TODO.md) for open tasks and [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT
