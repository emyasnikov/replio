# Replio vs. Pi

This document compares two open-source personal AI assistant / coding-agent projects: **Replio** (github.com/emyasnikov/replio) and **Pi Agent Harness** (github.com/earendil-works/pi). It highlights key design choices, runtime models, and ecosystem differences.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| Pi | TypeScript/JavaScript (Node + Bun) | https://github.com/earendil-works/pi | MIT | Monorepo with agent core, unified LLM API, coding-agent CLI, telemetry, and TUI |

## Architecture & Runtime Model

| Feature | Replio | Pi |
|---------|---------|----|
| Core runtime | Single Python process with a streaming agent loop | CLI that runs the agent core in the same process |
| Entry point | `replio` | `pi` |
| Runtime dependencies | None beyond stdlib | Node.js + Bun, npm |
| Deployment | Python package installed via `pipx`, no daemon | CLI run directly, standalone binaries built for releases |
| Multi-process | No | No, but the monorepo can run services separately |

Replio runs a tight loop that handles the REPL, CLI, and HTTP API. Tools load lazily and are extended by Python plugins. Pi is a monorepo. `@earendil-works/pi-agent-core` provides the agent runtime, `@earendil-works/pi-ai` a unified LLM provider layer, and `@earendil-works/pi-coding-agent` ships an interactive CLI that runs the agent runtime in the same process.

## Tooling & Function Calling

| Aspect | Replio | Pi |
|--------|---------|----|
| Built-in tools | web search, fetch page, file I/O, shell, permission gating (`allow`/`ask`/`deny`) | web search, fetch page, file I/O, shell, and custom `!` command syntax |
| Permission model | Path-scoped `allow`/`ask`/`deny` with runtime prompts | No built-in permission system, relies on OS sandboxing or Docker |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema |
| Extensibility | Python plugins register tools via a simple registry | Packages expose `@tool`/`@skill` decorators, monorepo architecture |

## Channels & UI

| Feature | Replio | Pi |
|---------|---------|----|
| Built-in UI | Terminal REPL only | Terminal UI library (`@earendil-works/pi-tui`), CLI only |
| Messaging channels | None | None (CLI only), `pi-chat` for Slack/chat automation |
| Web UI | None | None |
| TUI | Yes (basic REPL) | Yes (differential rendering) |

## Provider & Model Support

| Aspect | Replio | Pi |
|--------|---------|----|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, and any OpenAI-compatible endpoint | OpenAI, Anthropic, Google, and more via the unified API (`@earendil-works/pi-ai`) |
| Local model support | Built-in via Ollama | Built-in local providers via `@earendil-works/pi-ai` |

## Persistence & Telemetry

| Feature | Replio | Pi |
|---------|---------|----|
| Session persistence | Append-only JSON session logs, compaction | Telemetry contracts (`@earendil-works/pi-telemetry`), logs in workspace |
| State management | Simple conversation context | Agent runtime has a state stack, structured conversation state |
| Telemetry | None | Vendor-neutral telemetry contracts, reference adapter, conformance tests |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| Replio | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool |
| Pi | Runs with user permissions | Docker, micro-VM (Gondolin), OpenShell policy sandbox | Containerization recommended for stronger boundaries |

## Community & Ecosystem

| Project | License | Community | Plugin Ecosystem | Docs |
|---------|---------|-----------|-----------------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| Pi | MIT | Active, GitHub + X | npm packages in the monorepo | Docs on pi.dev, extensive containerization guide |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a lightweight, zero-dependency REPL you can embed or expose via a tiny HTTP API | Replio | Minimal Python runtime, no external deps |
| You need a coding agent with a unified LLM API, telemetry, and standalone binaries | Pi | Rich ecosystem, telemetry support, CLI or standalone binaries |
| You want stronger isolation out of the box | Pi | Built-in containerization and sandboxing docs |

## Summary Table

| Feature | Replio | Pi |
|---------|---------|----|
| Language | Python | TypeScript/JS + Bun |
| Runtime | Single process | CLI + core runtime |
| Extensibility | Python plugins | npm packages in monorepo |
| Channels | None | None (CLI only) |
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenAI-compatible | OpenAI, Anthropic, Google, and more |
| UI | Terminal REPL | Terminal TUI |
| Persistence | JSON session logs | Telemetry contracts |
| Isolation | Permission prompts | Docker / micro-VM recommended |
| Use case | Lightweight REPL + HTTP API | Coding agent with telemetry |

## References

- https://github.com/earendil-works/pi
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://pi.dev/docs/latest
