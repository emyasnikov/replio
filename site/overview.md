# Replio

**A lightweight, zero-dependency agentic core for fleets of single-purpose agents.**

Current version: **v0.26.0** (Python >= 3.10, MIT, zero external dependencies)

Replio is a deliberately small, auditable, zero-dependency agentic core built on a single streaming loop. The model plans, the tool registry acts, and the same loop powers an interactive REPL, a headless CLI, and an HTTP API. Each process is a self-contained agent scoped to one folder, with its own config, model, and tool permissions. Agents compose into larger systems through three orchestration layers - swarm (personas and delegation), jobs (scheduled, durable work), and fleet (a supervisor for many agents) - with MCP for cross-tool interoperability.

## Vision

**One terminal, whole teams.** One REPL. One prompt. The lead agent composes a specialized team - personas and skills instantiated from a private template library matching the project description and request - runs the team stage-by-stage, each member working under its own persona, skills, and permissions, with generated briefs, handoff, and shared memory. Teams are stored, reused, extended per customer, and scheduled.

Read the full vision, decisions, and context economics in [Vision](vision.md).

## Current state

- **Core** - one SSE-stream agent loop, multi-provider (Ollama, OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint), tool calling with per-tool permissions and an audit trail, plan/build modes, complete append-only session logs, plugins, `replio run` + `replio serve`
- **Orchestration** - swarm (personas, delegation), jobs (cron/interval/one-shot, retries, approvals, run memory), fleet (supervisor with ports, health, restart), MCP client and server
- **Latest** - v0.26 in progress: tool-use evaluation harness (`replio eval`), OpenCode Zen/Go providers. See [Changelog](changelog.md)
- **Tooling** - bundled plugins for web search, filesystem, shell, edit, git, and dev wrappers (test/lint/format), all with path-scoped policies

## Features

- **Zero dependencies** - everything is Python standard library. Nothing to audit, no supply chain, no lockfile churn
- **One agent loop** - a single SSE stream per turn powers the REPL, the CLI, and the API
- **Local-first** - config and session logs live on your disk. Bring your own provider key, or run fully local
- **Agentic REPL** - streaming output, dimmed thinking, markdown-aware rendering, readline history, tab completion
- **Permissions** - every tool is gated by `allow` / `ask` / `deny`, with path-scoped confirmation outside your worktree and an audit trail in session logs
- **Sessions** - complete append-only conversation logs plus `/compact` and Markdown export
- **Plugins** - external repositories register tools, providers, slash commands, and services. The core stays zero-dependency

## Development plan

The work packages and milestones live in [Roadmap](roadmap.md). The full task backlog (open work, newest first) is in [Backlog](backlog.md). The swarm/team track is the current priority - one terminal, whole teams - with the composition machinery kept in a movable private plugin, never in the core.

## Reference docs

The detailed reference is organized in the [Reference index](reference/index.md), covering architecture, commands, configuration, providers, tools, security, sessions, jobs, fleet, swarm, plugins, and more.

## Getting started

```bash
pipx install replio
replio
```

Or from source: `git clone https://github.com/emyasnikov/replio.git && cd replio`, then `python3 -m venv .venv && .venv/bin/pip install -e . && .venv/bin/replio`. First-time setup with `/connect`, then type any message.

## License

Replio is MIT licensed (see the LICENSE file in the repository).