# Replio vs. Hermes

This document compares two open-source AI agent projects: **Replio** (github.com/emyasnikov/replio) and **Hermes Agent** by Nous Research (github.com/NousResearch/hermes-agent). Both act through tool calling, but they target very different outcomes - Replio is a minimal agentic REPL core, while Hermes is a self-improving personal agent that runs anywhere and meets you in your messaging channels.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| Hermes | Python (uv) + Node.js | https://github.com/NousResearch/hermes-agent | MIT | Self-improving personal agent with memory, skills, multi-channel messaging, and remote/serverless execution |

## Architecture & Runtime Model

| Feature | Replio | Hermes |
|---------|--------|--------|
| Core runtime | Single Python process with a streaming agent loop | Single gateway process managing sessions, tools, and messaging |
| Front-ends | Terminal REPL, `replio run` (CLI), `replio serve` (HTTP JSON API) | CLI, TUI, desktop app, web dashboard, and messaging bots |
| Execution backends | Local only | Seven terminal backends - local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox (serverless) |
| Dependencies | None beyond stdlib | uv, Python 3.11, Node.js, ripgrep, ffmpeg |
| Deployment | Python package via `pipx`, no daemon | Installer for Linux/macOS/WSL/Windows/Termux, and runs on a `$5` VPS, GPU cluster, or serverless infra |

## Learning, Memory & Persistence

| Feature | Replio | Hermes |
|---------|--------|--------|
| Session persistence | Append-only JSON session logs with compaction | SQLite `state.db` sessions with FTS5 full-text search |
| Learning loop | None | Creates skills from experience and improves them during use |
| Memory | Per-session context only | Persistent `MEMORY.md`/`USER.md` injected into the system prompt, managed by the agent, plus external memory providers (Honcho, Mem0, and more) |
| Recall | None | `session_search` across all past conversations and a `/journey` learning timeline |
| Model of the user | None | Builds a deepening user profile across sessions |

This is Hermes's defining differentiator - a closed learning loop that persists knowledge, skills, and a user model across sessions. Replio is a stateless core that logs everything but learns nothing.

## Tooling & Function Calling

| Aspect | Replio | Hermes |
|--------|--------|--------|
| Built-in tools | Web search, fetch page, file I/O, shell, permission gating - via bundled plugin tools | 40+ tools in categories: web, browser automation, terminal/files, media, agent orchestration, memory, cron, MCP, Home Assistant |
| Tool organization | Plugin registry | Toolsets that can be enabled/disabled per platform |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema |
| Extensibility | Python plugins register tools/providers/commands | Skills (agentskills.io), MCP servers, plugins, Nous Tool Gateway |

## Channels & UI

| Feature | Replio | Hermes |
|---------|--------|--------|
| Built-in UI | Terminal REPL | CLI, TUI, desktop app, web dashboard |
| Messaging channels | None | Telegram, Discord, Slack, WhatsApp, Signal, Email - from one gateway process |
| Voice | None | Voice memo transcription and TTS |

## Provider & Model Support

| Aspect | Replio | Hermes |
|--------|--------|--------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, any OpenAI-compatible endpoint | Nous Portal (300+ models), OpenRouter, OpenAI, Anthropic, and many more |
| Model management | Single model, `reasoning` effort toggle | Main model plus 11 auxiliary slots (compression, vision, approval, and more), with a `hermes model` switch and no lock-in |
| Local models | Via Ollama | Via configured local endpoints |

## Security & Isolation

| Feature | Replio | Hermes |
|---------|--------|--------|
| Default isolation | Runs with user permissions | Runs with user permissions, with a strict approval model |
| Command approval | Path-scoped `allow`/`ask`/`deny` prompts | Dangerous-command approval (`smart`/`manual`/`off`), plus a hardline blocklist that even YOLO mode cannot bypass |
| Write safety | None beyond prompts | File-write denylist and optional `HERMES_WRITE_SAFE_ROOT` sandbox |
| Sandboxing | None | Hardened container isolation (Docker/Singularity/Modal/SSH), SSRF protection, MCP credential filtering, prompt-injection scanning, Tirith pre-exec scanning |
| Gateway auth | N/A | Allowlists, DM pairing codes, per-platform user controls |

## Automation & Delegation

| Feature | Replio | Hermes |
|---------|--------|--------|
| Scheduled tasks | None | Built-in cron scheduler with delivery to any platform |
| Delegation | Planned (roadmap - `delegate` tool, swarm) | Isolated subagents, background process management, PTY mode for interactive CLIs |

## Community & Ecosystem

| Project | License | Community | Ecosystem | Docs |
|---------|---------|-----------|-----------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| Hermes | MIT | Nous Research, active on GitHub and Discord | Skills Hub (agentskills.io), Nous Tool Gateway, can migrate from OpenClaw | hermes-agent.nousresearch.com/docs, extensive |

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
| Channels | None | Messaging plus CLI/TUI/desktop |
| Sandboxing | Permission prompts | Container isolation + write sandbox |
| Use case | Minimal embeddable agent core | Self-improving personal agent |

## References

- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs
