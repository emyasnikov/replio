# Replio vs. OpenCode

This document compares two open-source AI coding-agent projects: **Replio** (github.com/emyasnikov/replio) and **OpenCode** (github.com/anomalyco/opencode). Both run a tool-calling agent loop, but they differ in language, runtime model, tooling, and surface area.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Zero-dependency agentic core: REPL, CLI, HTTP API, types/teams delegation, jobs, fleet, MCP |
| OpenCode | TypeScript / JavaScript (Node + Bun) | https://github.com/anomalyco/opencode | MIT | Open-source AI coding agent for the terminal, desktop, and IDE |

## Runtime & Architecture

| Feature | Replio | OpenCode |
|---------|--------|----------|
| Core runtime | Single Python process with a streaming agent loop (one SSE stream per turn) | Node.js/Bun server plus TUI, desktop app, and IDE front-ends |
| Entry points | `replio` (REPL), `replio run`, `replio serve` (HTTP JSON API), `replio jobs`, `replio fleet`, `replio mcp` | `opencode` (TUI/CLI), desktop app (beta), IDE extension, `opencode-ai` npm package |
| Runtime dependencies | None beyond the Python >= 3.10 stdlib | Node.js + Bun, npm packages |
| Deployment | Python package via pip/pipx, local process, no daemon required | Homebrew tap, npm, Docker, desktop installers (macOS/Windows/Linux) |
| Multi-process | In-process sub-engines for delegation, no separate services | Server + TUI/desktop + IDE clients |

## Tools & Function Calling

| Aspect | Replio | OpenCode |
|--------|--------|----------|
| Built-in tools | Web search/fetch, file read/write/list/glob/grep, file edit, git, shell, test/lint/format wrappers, ask, delegate | Web search/fetch, file I/O, edit, bash, glob/grep, plus MCP-connected tools and a rich built-in set |
| Function-calling scheme | OpenAI-compatible JSON schema | OpenAI-compatible JSON schema via the Vercel AI SDK |
| Permission model | Path-scoped `allow`/`ask`/`deny` with confirm prompts, per-type tool permissions | Plan mode is read-only, build mode makes changes, runtime permission requests, auto-approve options |
| Extensibility | Python plugins register tools, providers, commands, services, types, teams, skills | Plugin SDK (`opencode-plugin`) for custom tools, agents, and UI extensions, npm packages |

## Channels & UI

| Feature | Replio | OpenCode |
|---------|--------|----------|
| Built-in UI | Terminal REPL (readline, tab completion, ANSI, markdown-aware streaming) | Advanced TUI with panels, code preview, diff view, multi-session |
| Desktop / IDE | None | Desktop app (beta), IDE extensions, multi-session parallel agents |
| Messaging channels | None | None (terminal/desktop/IDE only) |
| Web | `replio serve` HTTP JSON API | SDK server, share links for sessions |

## Providers & Models

| Aspect | Replio | OpenCode |
|--------|--------|----------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint, auto-detected from URL | 75+ providers via Models.dev, OpenCode Zen, GitHub Copilot, ChatGPT Plus/Pro login, local models |
| Local model support | Built-in via Ollama | Built-in via provider abstraction |

## Persistence & Memory

| Feature | Replio | OpenCode |
|---------|--------|----------|
| Session persistence | Append-only JSON session logs (`ses_`/`sub_`/`job_`), compaction, Markdown export | Structured session files with typed parts, resumable turns, JSON export |
| Cross-session memory | None (per-session context), job run memory files | None by default (privacy-first, does not store code or context) |
| Telemetry | None | Vendor-neutral telemetry contracts, optional OpenTelemetry |

## Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| Replio | Runs with user permissions | None (relies on permission prompts) | Path-scoped `allow`/`ask`/`deny` gates every tool, worktree escalation, audit trail |
| OpenCode | Runs with user permissions, plan mode read-only | Docker, policy-based sandboxing options | Desktop app runs sandboxed |

## Plugins & Docs

| Project | Plugin Ecosystem | Docs |
|---------|------------------|------|
| Replio | Directory plugins (tools, providers, commands, services, types, teams, skills, eval fixtures), bundled `replio-core-*` plugins, `/plugins` + `replio plugins` | Docs in repo (`docs/`), README |
| OpenCode | npm packages, plugin SDK, custom agents and UI extensions | opencode.ai docs, extensive developer guide |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You want a zero-dependency Python agent core to embed, script, or expose via a tiny HTTP API | Replio | Stdlib-only runtime, no install footprint, REPL + CLI + API |
| You want a full-featured coding agent with a rich TUI, desktop app, and IDE support, comfortable with Node.js | OpenCode | Large toolset, parallel sessions, desktop/IDE surfaces |
| You want stronger isolation out of the box | OpenCode | Docker and policy-based sandboxing |
| You want built-in job scheduling, fleet supervision, and agent delegation in one tool | Replio | Jobs daemon, fleet supervisor, types/teams/delegate built in |

## Summary Table

| Feature | Replio | OpenCode |
|---------|--------|----------|
| Language | Python (stdlib) | TypeScript/JS + Bun |
| Runtime | Single process | Server + TUI/desktop/IDE |
| Extensibility | Python plugins | npm plugin SDK |
| Channels | Terminal, HTTP API | Terminal, desktop, IDE |
| LLM providers | Ollama, OpenAI, Groq, Anthropic, OpenAI-compatible | 75+ via Models.dev, Zen, Copilot/ChatGPT login |
| UI | Terminal REPL | TUI + desktop app |
| Persistence | JSON session logs | Structured session files |
| Isolation | Permission prompts | Docker / policy sandbox |
| Use case | Embeddable agent core with orchestration | Full-featured coding agent with UI |

## References

- https://github.com/anomalyco/opencode
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://opencode.ai/docs
