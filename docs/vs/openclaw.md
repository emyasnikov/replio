# Replio vs. OpenClaw

This document compares two personal AI assistant projects: **Replio** (github.com/emyasnikov/replio) and **OpenClaw** (github.com/openclaw/openclaw). Both act through tool calling, but they differ in language, runtime model, and how they reach the user.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Zero-dependency agentic core: REPL, CLI, HTTP API, types/teams delegation, jobs, fleet, MCP |
| OpenClaw | TypeScript / JavaScript (Node.js) | https://github.com/openclaw/openclaw | MIT | Multi-channel personal assistant that runs on your devices and meets you in the channels you already use |

## Runtime & Architecture

| Feature | Replio | OpenClaw |
|---------|--------|----------|
| Core runtime | Single Python process with a streaming agent loop | Gateway daemon (control plane) managing sessions, tools, events, and channel connections |
| Entry points | `replio` (REPL), `replio run`, `replio serve`, `replio jobs`, `replio fleet`, `replio mcp` | `openclaw onboard --install-daemon`, `openclaw gateway`, `openclaw dashboard`, CLI and TUI |
| Runtime dependencies | None beyond the Python >= 3.10 stdlib | Node.js (22.22.3+, 24.15+, or 25.9+, Node 26 recommended). Installer available |
| Deployment | Python package via pip/pipx, local process | Gateway daemon (launchd/systemd), Control UI, CLI, TUI, Docker and Nix supported |
| Configuration | JSON: global `~/.config/replio/config.json` merged with local `.replio/config.json` | Workspace directory with configuration, logs, and plugin storage |
| Multi-agent | In-process sub-engines via types/teams/delegate | Multi-agent routing across workspaces and per-agent sessions |

## Tools & Function Calling

| Aspect | Replio | OpenClaw |
|--------|--------|----------|
| Built-in tools | Web search/fetch, file read/write/list/glob/grep, file edit, git, shell, test/lint/format wrappers, ask, delegate | Browser, canvas, nodes, cron, sessions, skills, plus voice, camera, screen capture, and more |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible function calling |
| Permission model | Path-scoped `allow`/`ask`/`deny` with confirm prompts, per-type tool permissions | Tools run on the host by default, sandboxing is configurable |
| Extensibility | Python plugins register tools, providers, commands, services, types, teams, skills | npm plugin SDK (`@tool`, `@skill`, `@channel`), plugins shared via ClawHub |

## Channels & UI

| Feature | Replio | OpenClaw |
|---------|--------|----------|
| Built-in UI | Terminal REPL | CLI, TUI, and a web Control UI |
| Messaging channels | None | WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, Matrix, Microsoft Teams, Zalo, and more (29 channels) |
| Companion apps | None | Voice, Canvas, camera, screen, and device-local actions on supported platforms |

## Providers & Models

| Aspect | Replio | OpenClaw |
|--------|--------|----------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint | Hosted, subscription-backed, gateway, and local models via a provider abstraction |
| Local model support | Built-in via Ollama | Built-in via local providers |

## Persistence & Memory

| Feature | Replio | OpenClaw |
|---------|--------|----------|
| Session persistence | Append-only JSON session logs with compaction | Gateway sessions persisted in the workspace directory |
| State management | Per-session context, job run memory | Sessions, tools, events, and channel connections managed by the gateway |
| Automation | Scheduled jobs (cron/interval/one-shot) with retries and approval | Cron via first-class tools and heartbeat checklists |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| Replio | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool, audit trail |
| OpenClaw | Tools run on the host for the main session | Sandboxing can be configured | DM-capable channels pair unknown senders by default, deterministic policy |

## Plugins & Docs

| Project | Plugin Ecosystem | Docs |
|---------|------------------|------|
| Replio | Directory plugins, bundled `replio-core-*` plugins, `/plugins` + `replio plugins` | Docs in repo (`docs/`), README |
| OpenClaw | npm plugin SDK, plugins shared via ClawHub, skills and channel plugins | docs.openclaw.ai, extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You want a zero-dependency Python agent core to embed, script, or expose via a tiny HTTP API | Replio | Stdlib-only runtime, no daemon, no external deps |
| You want an always-on assistant reachable from your messaging apps with a web UI, comfortable with Node.js | OpenClaw | Multi-channel gateway, Control UI, companion apps |
| You want to quickly prototype a tool-calling assistant without boilerplate | Replio | One streaming loop, simple tool registry |
| You need a background daemon managing long-running sessions across channels | OpenClaw | Gateway architecture built for that |

## Summary Table

| Feature | Replio | OpenClaw |
|---------|--------|----------|
| Language | Python (stdlib) | TypeScript/JavaScript |
| Runtime | Single process | Gateway daemon + front-ends |
| Extensibility | Python plugins | Node plugin SDK |
| Channels | Terminal, HTTP API | Many built-in |
| LLM providers | Ollama, OpenAI, Groq, Anthropic, OpenAI-compatible | Hosted, subscription, gateway, local |
| UI | Terminal REPL | CLI, TUI, Web Control UI |
| Persistence | JSON session logs | Gateway workspace |
| Isolation | Permission prompts | Configurable sandboxing |
| Use case | Embeddable agent core with orchestration | Multi-channel personal assistant |

Both share the goal of a personal AI assistant that acts through tool calling. They differ mainly in language, runtime model, and ecosystem. Pick the stack that aligns with your tech stack and operational requirements.

## References

- https://docs.openclaw.ai
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/openclaw/openclaw
