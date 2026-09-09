# Replio

**A lightweight, zero-dependency agentic core for fleets of single-purpose agents.**

<p>
  <a href="https://pypi.org/project/replio/"><img src="https://img.shields.io/pypi/v/replio" alt="PyPI version"></a>
  <a href="https://emyasnikov.github.io/replio/"><img src="https://img.shields.io/badge/docs-site-blue" alt="Site"></a>
  <img src="https://img.shields.io/badge/python-%3E%3D3.10-blue" alt="Python >=3.10">
  <img src="https://img.shields.io/github/actions/workflow/status/emyasnikov/replio/ci.yml?branch=main" alt="CI">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

Replio is a deliberately small, auditable, zero-dependency agentic core. The model plans, the tool registry acts, and a single streaming loop powers an interactive REPL, a headless CLI, and an HTTP API. Each process is a self-contained agent scoped to one folder, with its own config, model, and tool permissions. Agents compose into larger systems through three orchestration layers - swarm (types and delegation), jobs (scheduled, durable work), and fleet (a supervisor for many agents) - with MCP for cross-tool interoperability. All layers share one API and compose: a supervised fleet agent can delegate by type, a job can drive a team.

<p align="center"><img src="replio.svg" alt="Replio terminal session"></p>

## Features

### Core

- **Zero dependencies** - all Python standard library. Nothing to audit, no supply chain, no lockfile churn
- **One agent loop** - a single SSE stream per turn powers the REPL, the CLI, and the API, so front-ends share one code path. Headless: `replio run` for scripting, `replio serve` for an HTTP JSON API
- **Local-first** - config and session logs live on your disk. Bring your own provider key or run fully local
- **Multi-provider** - Ollama, OpenAI, Groq, Anthropic, OpenCode Zen/Go, plus any OpenAI-compatible endpoint, auto-detected from the base URL
- **Agentic REPL** - streaming token-by-token output, dimmed thinking, markdown-aware rendering, readline history, tab completion, and multi-line `"""` blocks
- **Tool calling** - web search and page fetch, file read/write/list/glob/grep/edit, git status/diff/commit, test/lint/format wrappers, and shell execution via OpenAI-compatible function calling or directly with `/tool`
- **Permissions** - every tool gated by `allow` / `ask` / `deny`, with path-scoped confirmation outside your worktree and an audit trail in session logs
- **Modes** - named postures with their own instructions and permissions: `plan` (read-only) vs `build`, or custom modes, switchable live with `/mode` or `--mode`
- **Sessions** - complete append-only conversation logs capturing every tool call, result, and error, plus `/compact` and Markdown export
- **Plugins** - external repositories register tools, providers, slash commands, services, agent types, teams, skills, and eval fixtures. The core stays zero-dependency. Plugin deps are imported lazily

### Orchestration

- **Swarm** - make agents cooperate. A type catalog (bundled defaults plus global/local `.replio/types.json`) and the `delegate` tool run a task under an agent type as an in-process sub-agent with its own `sub_*` session log, prompt, model override, and tool permissions. Manage types with `/types` (tag-filterable)
- **Jobs** - scheduled, durable workflows. Cron / interval / one-shot schedules, retries with exponential backoff, per-run timeouts, linked Markdown task files, a rolling run-memory summary, and human-in-the-loop approvals. Managed by `replio jobs`, `/jobs`, and the `replio jobs daemon`
- **Fleet** - run many scoped agents under one supervisor. `replio fleet` allocates conflict-free ports, health-checks every `replio serve` child, restarts failures with a bounded backoff, and generates per-agent configs, with `status`, `logs`, and `restart` for ops, foreground or detached
- **MCP (Model Context Protocol)** - work alongside other AI tools. Import external MCP servers' tools, or expose Replio's policy-filtered tools and session resources to other agents over `replio mcp` or `POST /mcp`

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

First-time setup with `/connect`, then type any message. Tab-complete `/` commands and session names, and navigate history with arrow keys. Open a `"""` or `'''` block to type a multi-line prompt. The framing quotes are stripped and the whole message is sent as one turn. Ctrl-C exits the REPL from anywhere, even inside an open block.

```
>>> /connect ollama
  API key [stored]:
Connected to ollama (https://api.ollama.com)
>>> /model gpt-oss:20b-cloud
>>> Hi
<<< Hello! How can I help you today?
>>> /exit
```

### CLI

Stream plain text with `--output text` or return JSON. Log tool status and diagnostics to stderr with `--verbose`. Address a persistent session with `--session-id <id>`. Tools that require confirmation auto-deny by default. Pass `--yes` to approve them.

```bash
replio run --prompt "Hi"
{
  "content": "Hello! How can I help you today?",
  "duration": 7.0,
  "errors": [],
  "model": "gpt-oss:20b-cloud",
  "provider": "ollama",
  "session": "ses_20260814_192251_hi",
  "status": "ok"
  "thinking": null,
  "tool_calls": [],
  "usage": null,
}
```

### API

`replio serve` exposes JSON endpoints. `POST /chat {"prompt": "..."}` (optionally with `"session_id"`) returns the same turn result as the CLI.

```bash
replio serve &
curl localhost:8787/chat -X POST -d '{"prompt": "Hi"}'
{"content": "Hello! How can I help you today?", "thinking": null, "tool_calls": [], "errors": [], "duration": 7.0, "usage": null, "model": "gpt-oss:20b-cloud", "provider": "ollama", "session": "ses_20260814_192711_hi", "status": "ok"}
```

### Swarm - delegation by type

A lead agent (or you) hands a task to a specialized type. The sub-agent runs in-process, writes its own session log, and returns its final answer. The REPL shows its dimmed activity and a duration footer while it works. Agent types are model- and permission-scoped: a researcher is read-only, a programmer may run shell.

```
>>> /types list
>>> /tool delegate {"type": "researcher", "task": "Summarize docs/ and cite sources"}
[delegate researcher] <final answer of the research sub-agent, sources cited>
```

See [docs/swarm.md](docs/swarm.md) and [docs/types.md](docs/types.md).

### Jobs - scheduled durable work

Jobs are human-gated workflows: `add` proposes, `approve` arms it, and the daemon fires it on schedule. The task lives in a Markdown file edited in `$EDITOR`. A rolling memory summary carries context between runs.

```bash
replio jobs add nightly --file tasks/nightly.md --cron "0 2 * * *"
replio jobs approve nightly
replio jobs daemon            # polls on --tick 15s, Ctrl-C to stop
replio jobs status
```

See [docs/jobs.md](docs/jobs.md).

### Fleet - supervised agents

One agent per folder, each a `replio serve` process with its own config, permissions, and sessions.

```bash
replio fleet init                                              # scan existing agent folders
replio fleet config docs-agent --type researcher --port 8781
replio fleet up                                                # Ctrl-C = graceful down, or --detach
replio fleet status
replio fleet logs docs-agent -f
```

See [docs/fleet.md](docs/fleet.md).

### MCP - interop with other AI tools

```bash
replio mcp    # stdio MCP server: serve Replio's tools/sessions or import another server's tools, e.g. point Claude or opencode at it
```

On `replio serve`, the same is available at `POST /mcp`. See [docs/mcp.md](docs/mcp.md).

## Roadmap

Fleet orchestration, scheduled and durable jobs, and the swarm foundations - bundled types, in-process sub-agents, the `delegate` tool, team pipelines (`/teams run`), and the `ask` tool - are live. Next: the governance track (first-run assistant introduction, one-window status over sessions, running agents, and jobs, agent health monitoring, per-agent todo lists), report-back connectors (webhook/email), the jobs operator API, non-blocking delegation with progress, the interactive `/agent` command, and remote channels. See [docs/swarm.md](docs/swarm.md), [docs/jobs.md](docs/jobs.md), and the open tasks in [TODO.md](TODO.md).

## Contributing

The project is stdlib-only with no external dependencies. See [AGENTS.md](AGENTS.md) for architecture and conventions, and [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## Documentation

The [website](https://emyasnikov.github.io/replio/) hosts the vision, development plan, and this documentation, rebuilt from `main` on every push. Detailed references live in [docs/index.md](docs/index.md).

## License

[MIT](LICENSE)
