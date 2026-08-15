# REPL.io vs. OpenClaw

This document provides a side‑by‑side comparison of the two open‑source personal AI assistant projects **REPL.io** and **OpenClaw**.  The goal is to surface their key design choices, capabilities, and trade‑offs.

## 1. Project Overview

| Feature | REPL.io | OpenClaw |
|---------|---------|----------|
| Primary language | Python | TypeScript/JavaScript (Node.js) |
| Core philosophy | Zero‑dependency, audit‑friendly, minimal footprint | Modular, plugin‑driven, full‑stack (CLI, Web UI, TUI, daemon) |
| Target audience | Developers who want a lightweight REPL + CLI + HTTP API | Solo operators who want a multi‑channel assistant that runs on their device |
| Installation | `pipx install replio` or `pip install -e .` | `curl … | bash` (auto‑installs Node), `npm install -g openclaw` |
| Deployment model | Single binary that runs locally, optional headless modes (`run`, `serve`) | Gateway daemon with optional web UI, TUI, or CLI; can run in Docker or Nix |
| Data persistence | Session logs stored in plain JSON on disk | Workspace directory with configuration, logs, and plugin storage |
| Configuration | Simple `.replio.toml` in home | `openclaw` command‑line config files under `~/.config/openclaw` |

## 2. Architecture & Core Loop

### REPL.io
- **One‑loop agent**: A single streaming loop powers REPL, CLI, and HTTP API.
- **Zero dependencies**: Uses only the Python standard library.
- **Tool registry**: Tools are defined in `tools.py` and are loaded lazily.
- **Plugins**: External repos can register tools, providers, and slash commands. The core stays dependency‑free; plugins are imported only when activated.
- **Session handling**: Append‑only JSON logs; compaction summarises long conversations.

### OpenClaw
- **Gateway architecture**: Central control plane that manages sessions, tools, events, and channel connections.
- **Daemon + UI**: Gateway can expose a web Control UI, TUI, or CLI. The UI is a separate front‑end that talks to the gateway via IPC/HTTP.
- **Plugin SDK**: Plugins are npm packages that expose tool, skill, and channel adapters.
- **Security model**: Out‑of‑process sandboxing possible; tools run on host by default.
- **Channel integration**: Built‑in adapters for WhatsApp, Telegram, Slack, Discord, etc.
- **Model providers**: Supports hosted and local providers (Ollama, OpenAI, Anthropic, etc.) via a provider abstraction.

**Key difference**: REPL.io bundles everything into a single executable with minimal runtime dependencies, while OpenClaw splits the control plane and front‑ends and uses Node's ecosystem for extensibility.

## 3. Tooling & Function Calling

| Aspect | REPL.io | OpenClaw |
|--------|---------|----------|
| Built‑in tools | web search, fetch page, file read/write/search, shell execution, permission gating (`allow/ask/deny`) | web search, fetch page, file I/O, shell, voice, canvas, camera, screen capture, etc. |
| Permission model | Path‑scoped `allow/ask/deny` with confirmation prompts | Explicit sandboxing via config; default host execution |
| Extensibility | Plugins register tools via a simple Python registry | Plugins expose `@tool`, `@skill`, `@channel` decorators; SDK enforces API contract |
| Function calling | OpenAI‑compatible function calling; tools are invoked via JSON schema | Uses same OpenAI function calling in skills; channel adapters manage messaging events |

## 4. Deployment & Runtime

### REPL.io
- **Portable**: No external runtime; just Python.
- **Headless modes**: `replio run` for scripts, `replio serve` for an HTTP JSON API.
- **No daemon**: Runs in the foreground; you can background it or use systemd.
- **Usage**: `replio`, `replio run`, `replio serve`.

### OpenClaw
- **Gateway daemon**: `openclaw onboard`, `openclaw gateway status`, `openclaw dashboard`.
- **Multiple runtimes**: Node 22+, Docker, Nix, etc.
- **Auto‑install**: Bootstrap script installs Node if missing.
- **UI**: Web Control UI (React), TUI (Terminal UI), CLI.
- **Channels**: Each channel is a separate adapter that can run as a plugin.

## 5. Community & Contributions

- **REPL.io**: MIT license, contributions via pull requests, focus on minimalism; docs in `docs/`.
- **OpenClaw**: MIT license with a non‑profit foundation, active on Discord, GitHub, and ClawHub; contributions accepted via PRs; plugin SDK encourages ecosystem growth.

## 6. When to Choose Which

| Scenario | Preferred Project |
|----------|-------------------|
| You need a lightweight, zero‑dependency REPL that you can embed in scripts or expose via a tiny HTTP API | REPL.io |
| You want a full‑featured assistant that connects to many messaging platforms, has a web UI, and you’re comfortable with Node.js | OpenClaw |
| You want to quickly prototype a tool‑calling assistant without writing a lot of boilerplate | REPL.io |
| You need to expose the assistant as a daemon that can run in the background and manage long‑running sessions | OpenClaw |

## 7. Summary

| Aspect | REPL.io | OpenClaw |
|--------|---------|----------|
| Language | Python | TypeScript/JavaScript |
| Dependency footprint | Zero | Moderate (Node, pnpm) |
| Extensibility | Python plugins | Node plugin SDK |
| Deployment | Single binary, no daemon | Gateway daemon + UI |
| Channels | None built‑in | Many built‑in |
| Ideal for | Quick, local REPL and CLI | Full‑stack, multi‑channel assistant |

Both projects share a common goal: to provide a **personal AI assistant** that can perform actions via tool calling. They differ mainly in language, runtime model, and ecosystem. Pick the stack that aligns with your existing tech stack and operational requirements.

## 8. References

- REPL.io: <https://github.com/emyasnikov/replio>
- OpenClaw: <https://github.com/openclaw/openclaw>
- REPL.io Docs: <https://github.com/emyasnikov/replio/tree/main/docs>
- OpenClaw Docs: <https://docs.openclaw.ai>
