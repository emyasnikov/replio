# Replio

**An lightweight tooling core for fleets of single-purpose agents.**

<p>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python >=3.10">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/pypi/v/replio" alt="PyPI version">
  <img src="https://img.shields.io/github/actions/workflow/status/emyasnikov/replio/ci.yml?branch=main" alt="CI">
</p>

Replio is deliberately small and auditable zero-dependency agentic core built on a single streaming loop. The model plans, the tool registry acts, and the same loop powers an interactive REPL, headless CLI or HTTP API. Each process is a self-contained, scoped agent in one folder with its config, model and tool permissions. Light enough for one machine to hold a fleet of focused agents.

<p align="center"><img src="replio.svg" width="540" alt="Replio terminal session"></p>

## Features

- **Zero dependencies** - everything is Python standard library. Nothing to audit, no supply chain, no lockfile churn
- **One agent loop** - a single SSE stream per turn powers the REPL, the CLI and the API. No duplicated logic across front-ends
- **Local-first** - config and session logs live on your disk. Bring your own provider key, or run fully local
- **Agentic REPL** - streaming token-by-token output, dimmed thinking, markdown-aware rendering, readline history and tab completion
- **Tool calling** - web search, page fetching, file read/write/search and shell execution via OpenAI-compatible function calling
- **Permissions** - every tool is gated by `allow` / `ask` / `deny`, with path-scoped confirmations for anything outside your worktree
- **Plugins** - external repositories register tools, providers and slash commands. The core stays zero-dependency, and plugin deps are imported lazily, only when you activate a plugin
- **Multi-provider** - Ollama, OpenAI, Groq, Anthropic, plus any OpenAI-compatible endpoint, with automatic detection from the base URL
- **Sessions** - complete append-only conversation logs, including every tool call and its result
- **Compaction** - summarize long conversations and trim the provider context without losing history
- **Headless modes** - `replio run` for scripting and `replio serve` for an HTTP JSON API
- **Agent fleets** - one process per single-purpose agent, scoped to its own folder, config and permissions

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

First-time setup with `/connect`, then type any message. Tab-complete `/` commands and session names. Use arrow keys to navigate history.

```
>>> /connect
  Provider [ollama]:
  Base URL [https://ollama.com]:
  API key: ...
  Model [gpt-oss:20b-cloud]:
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

Server exposes JSON endpoints like `POST /chat {"prompt": "..."}` (optionally `{"session_id": ...}`) returns the same turn result as the CLI.

```bash
replio serve &
curl localhost:8787/chat -X POST -d '{"prompt": "Hi"}'
{"content": "Hello! How can I help you today?", "thinking": null, "tool_calls": [], "errors": [], "duration": 7.0, "usage": null, "model": "gpt-oss:20b-cloud", "provider": "ollama", "session": "20260814_192711_hi", "status": "ok"}
```

### Agent fleets

Each `replio serve` process is an agent scoped to its folder. The tool policy confines file access to that folder, and headless agents auto-deny anything that asks for confirmation, so an agent can only reach its own worktree.

```bash
replio serve --path docs --port 8781 &
replio serve --path src --port 8782 &
```

Agents talk to each other through the same `POST /chat` API. See [docs/fleet.md](docs/fleet.md) for the full pattern and deployment templates.

## Roadmap

Fleet orchestration (running many scoped agents under a supervisor) and swarm orchestration (agents cooperating through personas and delegation) are the two orchestration layers being built next. See [docs/fleet.md](docs/fleet.md) and [docs/swarm.md](docs/swarm.md). Open tasks live in [TODO.md](TODO.md).

## Contributing

The project is stdlib-only with no external dependencies. See [AGENTS.md](AGENTS.md) for architecture and conventions, and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## Documentation

Detailed references are in the [docs](docs/):

- [API endpoints](docs/api.md)
- [Configuration](docs/config.md)
- [Commands & CLI](docs/commands.md)
- [Plugins](docs/plugins.md)
- [Agent fleets](docs/fleet.md)
- [Agent swarms](docs/swarm.md)
- [Deployment](docs/deploy.md)

## License

[MIT](LICENSE)
