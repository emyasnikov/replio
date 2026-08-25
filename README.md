# Replio

**An lightweight tooling core for fleets of single-purpose agents.**

<p>
  <a href="https://pypi.org/project/replio/"><img src="https://img.shields.io/pypi/v/replio" alt="PyPI version"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python >=3.10">
  <img src="https://img.shields.io/github/actions/workflow/status/emyasnikov/replio/ci.yml?branch=main" alt="CI">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
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
- **Modes** - named postures with their own instructions and permissions: `plan` (read-only) vs `build`, or custom modes, switchable live with `/mode` or via `--mode`
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

Open a `"""` or `'''` block to type a multi-line prompt. The block's framing quotes are stripped, and the whole message is sent as one turn. Ctrl-C exits the REPL from anywhere, including inside an open block.

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

### Agent orchestration

Three ways to combine Replio into larger systems:

- **MCP (Model Context Protocol)** - work alongside other AI tools. Connect to external MCP servers (stdio or HTTP) to import their tools, or expose Replio's own tools and sessions as an MCP server for other agents (Claude, opencode, ...) via `replio mcp` or `POST /mcp` on `replio serve`. See [docs/mcp.md](docs/mcp.md)
- **Swarm** - make agents cooperate: a persona catalog (bundled defaults plus global/local `.replio/personas.json`), the `delegate` tool that runs a task under a persona as an in-process sub-agent with its own session log, and `/persona` for management, so a lead agent splits work across specialized sub-agents. See [docs/swarm.md](docs/swarm.md) and [docs/personas.md](docs/personas.md)
- **Fleet** - run many scoped agents side by side, each a `replio serve` process confined to its own folder, worktree and permissions, orchestrated under a supervisor. See [docs/fleet.md](docs/fleet.md)

Fleet and swarm are two layers: fleet keeps agents alive, swarm gets the job done, and both compose with MCP for cross-tool interoperability.

## Roadmap

The swarm foundations are live - personas (bundled catalog + `/persona`), the in-process sub-agent engine, and the `delegate` tool. Building next: fleet orchestration (running many scoped agents under a supervisor), auditor agents and generate > check > correct, the interactive `/agent` command and delegation focus, and jobs/team orchestration. See [docs/fleet.md](docs/fleet.md) and [docs/swarm.md](docs/swarm.md). Open tasks live in [TODO.md](TODO.md).

## Contributing

The project is stdlib-only with no external dependencies. See [AGENTS.md](AGENTS.md) for architecture and conventions, and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## Documentation

Detailed references are in the [docs/INDEX.md](docs/INDEX.md)

## License

[MIT](LICENSE)
