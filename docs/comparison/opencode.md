# Replio vs. OpenCode

This document compares two open-source AI coding-agent / personal assistant projects: **Replio** (github.com/emyasnikov/replio) and **OpenCode** (github.com/anomalyco/opencode). They share the goal of a tool-calling agent loop, but differ in language, architecture, deployment model, tooling, and community focus.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| OpenCode | TypeScript / JavaScript (Node / Bun) | https://github.com/anomalyco/opencode | MIT | Full-stack AI coding agent with terminal UI, desktop app, and multi-agent workflow |

## Architecture & Runtime Model

| Feature | Replio | OpenCode |
|---------|---------|----------|
| Core runtime | Single Python process with a streaming agent loop | Node.js + Bun CLI that launches an agent core and a web/desktop UI in separate processes |
| Entry point | `replio` | `opencode` (CLI) or `opencode-ai` (npm) |
| Runtime dependencies | None beyond stdlib | Node.js + Bun, npm, optional desktop bundler |
| Deployment | Python package installed via `pipx`, no daemon | CLI plus optional desktop app, Docker, Homebrew, Scoop, or Chocolatey |
| Multi-process | No | Yes (CLI + UI + optional desktop) |

## Tooling & Function Calling

| Aspect | Replio | OpenCode |
|--------|---------|----------|
| Built-in tools | web search, fetch page, file I/O, shell, permission gating | web search, fetch page, file I/O, shell, Git, Docker, npm, and more (rich toolset) |
| Permission model | Path-scoped `allow`/`ask`/`deny` with runtime prompts | Plan mode is read-only, build mode makes changes, permissions requested at runtime |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema |
| Extensibility | Python plugins via a simple registry | npm packages and a plugin SDK (`opencode-plugin`) for custom tools, agents, and UI extensions |

## Channels & UI

| Feature | Replio | OpenCode |
|---------|---------|----------|
| Built-in UI | Terminal REPL only | Terminal UI, optional desktop app, and IDE extension |
| Messaging channels | None | None (CLI/desktop/IDE only) |
| Web UI | None | None (web/desktop wrappers exist) |
| TUI | Basic REPL | Advanced TUI with panel layout, code preview, and diff view |

## Provider & Model Support

| Aspect | Replio | OpenCode |
|--------|---------|----------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, and any OpenAI-compatible endpoint | OpenAI, Anthropic, Gemini, local via Ollama, and any configured provider |
| Local model support | Built-in via Ollama | Built-in via the provider abstraction |

## Persistence & Telemetry

| Feature | Replio | OpenCode |
|---------|---------|----------|
| Session persistence | Append-only JSON session logs, compaction | Logs under `~/.opencode/logs`, telemetry contracts |
| State management | Simple conversation context | Agent context stack, multi-agent workflow (build, plan) |
| Telemetry | None | Vendor-neutral telemetry contracts, optional integration with external backends |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| Replio | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool |
| OpenCode | Runs with user permissions, plan mode is read-only | Docker, optional policy-based sandboxing | Desktop app runs sandboxed |

## Community & Ecosystem

| Project | License | Community | Plugin Ecosystem | Docs |
|---------|---------|-----------|-----------------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| OpenCode | MIT | Active on GitHub and Discord | npm packages, plugin SDK | Docs on opencode.ai, extensive developer guide |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a lightweight REPL with zero external dependencies you can embed or expose via a tiny HTTP API | Replio | Minimal Python runtime, no OS dependencies |
| You want a full-featured AI coding agent with a rich terminal UI and optional desktop app, and you are comfortable with Node.js | OpenCode | Rich toolset, multi-agent workflow, desktop app, advanced UI |
| You want stronger isolation out of the box | OpenCode | Docker and policy-based sandboxing |

## Summary Table

| Feature | Replio | OpenCode |
|---------|---------|----------|
| Language | Python | TypeScript/JS + Bun |
| Runtime | Single process | CLI + UI + optional desktop |
| Extensibility | Python plugins | npm plugin SDK |
| Channels | None | None (CLI/desktop/IDE only) |
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenAI-compatible | OpenAI, Anthropic, Gemini, local via Ollama |
| UI | Terminal REPL | Terminal UI + desktop app |
| Persistence | JSON session logs | Telemetry contracts and logs |
| Isolation | Permission prompts | Docker / policy sandbox |
| Use case | Lightweight REPL + HTTP API | Full-featured coding agent with UI |

## References

- Replio: https://github.com/emyasnikov/replio
- OpenCode: https://github.com/anomalyco/opencode
- OpenCode docs: https://opencode.ai/docs
- Replio docs: https://github.com/emyasnikov/replio/tree/main/docs
