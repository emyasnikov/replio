# Replio vs. Hermes

This document compares two open-source AI agent projects: **Replio** (github.com/emyasnikov/replio) and **Hermes Agent** by Nous Research (github.com/NousResearch/hermes-agent). Both act through tool calling, but they target different outcomes: Replio is a minimal zero-dependency agentic core, while Hermes is a self-improving personal agent that runs anywhere and meets you in your messaging channels.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Zero-dependency agentic core: REPL, CLI, HTTP API, types/teams delegation, jobs, fleet, MCP |
| Hermes | Python (uv) + Node.js | https://github.com/NousResearch/hermes-agent | MIT | Self-improving personal agent with memory, skills, multi-channel messaging, and remote/serverless execution |

## Runtime & Architecture

| Feature | Replio | Hermes |
|---------|--------|--------|
| Core runtime | Single Python process with a streaming agent loop | Single gateway process managing sessions, tools, and messaging |
| Front-ends | Terminal REPL, `replio run`, `replio serve` (HTTP JSON API) | CLI, TUI, desktop app, web dashboard, and messaging bots |
| Execution backends | Local only | Seven terminal backends: local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox |
| Dependencies | None beyond the Python >= 3.10 stdlib | uv, Python, Node.js, plus optional tooling |
| Deployment | Python package via pip/pipx, no daemon required | Installer for Linux/macOS/WSL/Windows/Termux, runs on a VPS, GPU cluster, or serverless infrastructure |

## Learning, Memory & Persistence

| Feature | Replio | Hermes |
|---------|--------|--------|
| Session persistence | Append-only JSON session logs with compaction | SQLite `state.db` sessions with FTS5 full-text search |
| Learning loop | None | Creates skills from experience and improves them during use |
| Memory | Per-session context only | Persistent `MEMORY.md`/`USER.md` injected into the system prompt, managed by the agent, plus pluggable memory providers (Honcho and more) |
| Recall | None | `session_search` across past conversations and a learning timeline |
| Model of the user | None | Builds a deepening user profile across sessions |

This is Hermes's defining differentiator: a closed learning loop that persists knowledge, skills, and a user model across sessions. Replio is a stateless core that logs everything but learns nothing.

## Tools & Function Calling

| Aspect | Replio | Hermes |
|--------|--------|--------|
| Built-in tools | Web search/fetch, file read/write/list/glob/grep, file edit, git, shell, test/lint/format wrappers, ask, delegate | 40+ tools in categories: web, browser automation, terminal/files, media, agent orchestration, memory, cron, MCP, Home Assistant |
| Tool organization | Plugin registry | Toolsets that can be enabled/disabled per platform |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema |
| Extensibility | Python plugins register tools, providers, commands, services, types, teams, skills | Skills (agentskills.io), MCP servers, plugins, Nous Tool Gateway |

## Channels & UI

| Feature | Replio | Hermes |
|---------|--------|--------|
| Built-in UI | Terminal REPL | CLI, TUI, desktop app, web dashboard |
| Messaging channels | None | Telegram, Discord, Slack, WhatsApp, Signal, Email, Home Assistant |
| Voice | None | Voice memo transcription and TTS |

## Providers & Models

| Aspect | Replio | Hermes |
|--------|--------|--------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint | Nous Portal (300+ models), OpenRouter, OpenAI, Anthropic, and many more |
| Model management | Single model, `reasoning` effort toggle | Main model plus auxiliary slots (compression, vision, approval, and more), `hermes model` switch |
| Local models | Via Ollama | Via configured local endpoints |

## Automation & Delegation

| Feature | Replio | Hermes |
|---------|--------|--------|
| Scheduled tasks | Jobs: cron/interval/one-shot, retries, per-run approval, rolling run memory | Built-in cron scheduler with delivery to any platform |
| Delegation | `delegate` tool and team stages via in-process sub-engines, own session logs | Isolated subagents, background process management, RPC scripts, PTY mode for interactive CLIs |

## Security & Isolation

| Feature | Replio | Hermes |
|---------|--------|--------|
| Default isolation | Runs with user permissions | Runs with user permissions, with a strict approval model |
| Command approval | Path-scoped `allow`/`ask`/`deny` prompts | Dangerous-command approval (`smart`/`manual`/`off`), plus a hardline blocklist |
| Write safety | None beyond prompts | File-write denylist and optional `HERMES_WRITE_SAFE_ROOT` sandbox |
| Sandboxing | None | Hardened container isolation (Docker/Singularity/Modal/SSH), SSRF protection, credential filtering |
| Gateway auth | N/A | Allowlists, DM pairing codes, per-platform user controls |

## Plugins & Docs

| Project | Plugin Ecosystem | Docs |
|---------|------------------|------|
| Replio | Directory plugins, bundled `replio-core-*` plugins, `/plugins` + `replio plugins` | Docs in repo (`docs/`), README |
| Hermes | Skills Hub (agentskills.io), Nous Tool Gateway, MCP, can migrate from OpenClaw | hermes-agent.nousresearch.com/docs, extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a minimal, zero-dependency agent core to embed in scripts, run in CI, or expose via a tiny HTTP API | Replio | Single Python process, stdlib only, no daemon |
| You want a self-improving personal agent that remembers you, runs where you do, and talks to you in your messaging apps | Hermes | Persistent memory, skills, multi-channel gateway, remote/serverless backends |
| You want strong isolation with a working sandbox out of the box | Hermes | Container backends, command approval, write sandbox |
| You want a stateless, fully auditable agent log you control | Replio | Append-only session logs, local-first |

## Summary Table

| Feature | Replio | Hermes |
|---------|--------|--------|
| Language | Python (stdlib) | Python + Node.js |
| Runtime | Single process, local | Gateway + multi-channel + remote backends |
| Learning loop | None | Memory, skills, user model |
| Persistence | JSON session logs | SQLite + FTS5 + memory files |
| Channels | Terminal, HTTP API | Messaging plus CLI/TUI/desktop |
| Scheduling | Jobs daemon | Cron with platform delivery |
| Sandboxing | Permission prompts | Container isolation + write sandbox |
| Use case | Minimal embeddable agent core | Self-improving personal agent |

## References

- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs
