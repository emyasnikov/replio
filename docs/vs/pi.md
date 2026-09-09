# Replio vs. Pi

This document compares two open-source AI coding-agent / personal assistant projects: **Replio** (github.com/emyasnikov/replio) and **Pi Agent Harness** (github.com/earendil-works/pi). Both run an agent loop in a terminal, but they differ in language, architecture, and philosophy: Replio ships orchestration (types, teams, jobs, fleet, MCP) in a zero-dependency core, while Pi is a minimal harness you extend with packages.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Zero-dependency agentic core: REPL, CLI, HTTP API, types/teams delegation, jobs, fleet, MCP |
| Pi | TypeScript / JavaScript (Node + Bun) | https://github.com/earendil-works/pi | MIT | Minimal, self-extensible agent harness: agent core, unified LLM API, TUI, telemetry, coding-agent CLI |

## Runtime & Architecture

| Feature | Replio | Pi |
|---------|--------|----|
| Core runtime | Single Python process with a streaming agent loop | CLI that runs the agent core in the same process, with an RPC mode and SDK |
| Entry points | `replio` (REPL), `replio run`, `replio serve`, `replio jobs`, `replio fleet`, `replio mcp` | `pi` in four modes: interactive, print/JSON, RPC, SDK |
| Runtime dependencies | None beyond the Python >= 3.10 stdlib | Node.js + Bun, npm packages |
| Deployment | Python package via pip/pipx, no daemon | CLI run directly, standalone binaries built for releases |
| Packages | Core plus bundled plugins | Monorepo: `@earendil-works/pi-agent-core`, `-ai`, `-tui`, `-telemetry`, `-chord`, `-client`, `-protocol`, `-storage-sqlite-node` |

Replio runs a tight loop that handles the REPL, CLI, and HTTP API, with orchestration built in. Pi is a monorepo where the agent runtime, a unified LLM provider layer, a terminal UI library, and a coding-agent CLI ship as separate packages you compose.

## Tools & Function Calling

| Aspect | Replio | Pi |
|--------|---------|----|
| Built-in tools | Web search/fetch, file read/write/list/glob/grep, file edit, git, shell, test/lint/format wrappers, ask, delegate | `read`, `write`, `edit`, `bash`, plus a `!` command syntax |
| Permission model | Path-scoped `allow`/`ask`/`deny` with confirm prompts, per-type tool permissions | No built-in permission system, relies on OS sandboxing or containers |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema |
| Extensibility | Python plugins register tools, providers, commands, services, types, teams, skills | TypeScript extensions, skills, prompt templates, themes, Pi packages from npm/git |

Pi deliberately skips features like sub-agents, plan mode, and permission gates by default. You build them with extensions, skills, or installed packages, or ask Pi to build them.

## Channels & UI

| Feature | Replio | Pi |
|---------|--------|----|
| Built-in UI | Terminal REPL | Terminal UI library with differential rendering (`@earendil-works/pi-tui`), CLI only |
| Messaging channels | None | None (CLI only) |
| Web UI | None | None |
| Remote | `replio serve` HTTP JSON API | RPC mode and SDK, used by OpenClaw as a real-world integration |

## Providers & Models

| Aspect | Replio | Pi |
|--------|--------|----|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint | OpenAI, Anthropic, Google, and more via the unified API (`@earendil-works/pi-ai`) |
| Local model support | Built-in via Ollama | Built-in local providers via `@earendil-works/pi-ai` |

## Persistence & Telemetry

| Feature | Replio | Pi |
|---------|--------|----|
| Session persistence | Append-only JSON session logs, compaction, Markdown export | Sessions in the agent directory, SQLite session backend, JSON export |
| State management | Simple conversation context | Agent runtime with a state stack and structured conversation state |
| Telemetry | None | Vendor-neutral telemetry contracts (`@earendil-works/pi-telemetry`), install/update telemetry, offline mode |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| Replio | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool, audit trail |
| Pi | Runs with user permissions | Gondolin micro-VM, plain Docker, OpenShell policy sandbox | Containerization recommended for stronger boundaries |

## Plugins & Docs

| Project | Plugin Ecosystem | Docs |
|---------|------------------|------|
| Replio | Directory plugins, bundled `replio-core-*` plugins, `/plugins` + `replio plugins` | Docs in repo (`docs/`), README |
| Pi | npm packages in the monorepo, extensions, skills, prompt templates, themes | Docs on pi.dev, extensive containerization guide |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You want a zero-dependency agent core with built-in orchestration to script or expose via HTTP | Replio | Stdlib-only Python, jobs/fleet/teams built in |
| You want a minimal coding agent with a unified LLM API, telemetry, and standalone binaries you extend yourself | Pi | Extensible monorepo, telemetry support, CLI or standalone binaries |
| You want stronger isolation out of the box | Pi | Built-in containerization and sandboxing docs |

## Summary Table

| Feature | Replio | Pi |
|---------|--------|----|
| Language | Python (stdlib) | TypeScript/JS + Bun |
| Runtime | Single process | CLI + core runtime |
| Extensibility | Python plugins | npm packages in monorepo |
| Channels | Terminal, HTTP API | None (CLI only) |
| LLM providers | Ollama, OpenAI, Groq, Anthropic, OpenAI-compatible | OpenAI, Anthropic, Google, and more |
| UI | Terminal REPL | Terminal TUI |
| Persistence | JSON session logs | Session files, SQLite backend |
| Isolation | Permission prompts | Docker / micro-VM recommended |
| Use case | Embeddable core with orchestration | Self-extensible coding harness |

## References

- https://github.com/earendil-works/pi
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://pi.dev/docs/latest
