# REPL.io vs. OpenClaw

This document compares two open-source personal AI assistant projects: **REPL.io** (github.com/emyasnikov/replio) and **OpenClaw** (github.com/openclaw/openclaw). Both are single-operator assistants that act through tool calling, but they differ in language, runtime model, and how they reach the user.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| REPL.io | Python | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| OpenClaw | TypeScript/JavaScript (Node.js) | https://github.com/openclaw/openclaw | MIT | Multi-channel personal assistant that runs on your devices and meets you in the channels you already use |

## Architecture & Runtime Model

| Feature | REPL.io | OpenClaw |
|---------|---------|----------|
| Core runtime | Single Python process with a streaming agent loop | Gateway daemon (control plane) that manages sessions, tools, events, and channel connections |
| Entry point | `replio` | `openclaw onboard --install-daemon`, `openclaw gateway status`, `openclaw dashboard` |
| Runtime dependencies | None beyond stdlib | Node.js 22.22.3+ (or 24.15+, 25.9+) |
| Deployment | Python package installed via `pipx`, no daemon | Gateway daemon plus optional Control UI, TUI, or CLI; Docker and Nix supported |
| Front-ends | Terminal REPL, `replio run` (CLI), `replio serve` (HTTP API) | Control UI (web), TUI, and CLI — all front-ends talk to the gateway |
| Configuration | JSON: global `~/.config/replio/config.json` merged with local `.replio/config.json` | Workspace directory with configuration, logs, and plugin storage |
| Extensibility | Python plugins register tools, providers, and commands; core stays dependency-free | npm plugin SDK (`@tool`, `@skill`, `@channel`); plugins shared via ClawHub |

The two projects make different trade-offs. REPL.io bundles everything into a single Python process with a minimal footprint, while OpenClaw splits the control plane from its front-ends and leans on the Node ecosystem for extensibility.

## Tooling & Function Calling

| Aspect | REPL.io | OpenClaw |
|--------|---------|----------|
| Built-in tools | web search, fetch page, file read/write/search, shell execution | web search, fetch page, file I/O, shell, voice, canvas, camera, screen capture, and more |
| Tool delivery | Ship as bundled plugins (`replio-core-websearch`, `replio-core-fs`, `replio-core-exec`) | Built into the gateway and extensible via plugins |
| Permission model | Path-scoped `allow`/`ask`/`deny` with confirmation prompts | Tools run on the host by default; sandboxing is configurable |
| Function calling | OpenAI-compatible JSON schema | OpenAI-compatible function calling |
| Extensibility | Plugins register tools via a simple Python registry | Plugins expose `@tool`, `@skill`, `@channel` decorators; SDK enforces the API contract |

## Channels & UI

| Feature | REPL.io | OpenClaw |
|---------|---------|----------|
| Built-in UI | Terminal REPL | CLI, TUI, and a web Control UI |
| Messaging channels | None | WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, and other messaging services |
| Companion apps | None | Optional apps and nodes add voice, canvas, camera, screen, and device-local actions |

## Provider & Model Support

| Aspect | REPL.io | OpenClaw |
|--------|---------|----------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, and any OpenAI-compatible endpoint | Hosted and local model providers via a provider abstraction |
| Local model support | Built-in via Ollama | Built-in via local providers |

## Persistence & Telemetry

| Feature | REPL.io | OpenClaw |
|---------|---------|----------|
| Session persistence | Append-only JSON session logs with compaction | Gateway sessions persisted in the workspace directory |
| State management | Simple conversation context per session | Sessions, tools, events, and channel connections managed by the gateway |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| REPL.io | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool |
| OpenClaw | Tools run on the host for the main session | Sandboxing can be configured | DM-capable channels pair unknown senders by default |

## Community & Ecosystem

| Project | License | Community | Plugin Ecosystem | Docs |
|---------|---------|-----------|-----------------|------|
| REPL.io | MIT | Small, GitHub-centric | Python plugins | Docs in repo; minimal |
| OpenClaw | MIT | Developed in the open by the OpenClaw Foundation; active on GitHub, Discord, and ClawHub | npm plugin SDK; plugins shared via ClawHub | docs.openclaw.ai; extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a lightweight, zero-dependency REPL you can embed in scripts or expose via a tiny HTTP API | REPL.io | Minimal Python runtime, no external deps, no daemon |
| You want a full-featured assistant that connects to messaging platforms and has a web UI, and you are comfortable with Node.js | OpenClaw | Multi-channel support, Control UI, and companion apps |
| You want to quickly prototype a tool-calling assistant without boilerplate | REPL.io | One streaming loop, one round trip, simple tool registry |
| You need a background daemon that manages long-running sessions across channels | OpenClaw | Gateway architecture built for that |

## Summary Table

| Feature | REPL.io | OpenClaw |
|---------|---------|----------|
| Language | Python | TypeScript/JavaScript |
| Runtime | Single process | Gateway daemon + front-ends |
| Extensibility | Python plugins | Node plugin SDK |
| Channels | None built-in | Many built-in |
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenAI-compatible | Hosted and local providers |
| UI | Terminal REPL | CLI, TUI, Web Control UI |
| Persistence | JSON session logs | Gateway workspace |
| Isolation | Permission prompts | Configurable sandboxing |
| Use case | Lightweight REPL, CLI, and HTTP API | Multi-channel personal assistant |

Both projects share a common goal: a personal AI assistant that acts through tool calling. They differ mainly in language, runtime model, and ecosystem. Pick the stack that aligns with your tech stack and operational requirements.

## References

- REPL.io: https://github.com/emyasnikov/replio
- OpenClaw: https://github.com/openclaw/openclaw
- REPL.io docs: https://github.com/emyasnikov/replio/tree/main/docs
- OpenClaw docs: https://docs.openclaw.ai
