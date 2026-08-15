# REPL.io vs. OpenCode

This document provides a side‑by‑side comparison between **REPL.io** (github.com/emyasnikov/replio) and **OpenCode** (github.com/anomalyco/opencode). Both are open‑source personal AI assistant / coding‑agent projects, but they differ in language, architecture, deployment model, tooling, and community focus.

## 1. Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| REPL.io | Python | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| OpenCode | TypeScript / JavaScript (Node / Bun) | https://github.com/anomalyco/opencode | MIT | Full‑stack AI coding agent with terminal UI, desktop app, and multi‑agent workflow |

## 2. Architecture & Runtime Model

| Feature | REPL.io | OpenCode |
|---------|---------|----------|
| Core runtime | Single Python process with a streaming loop | Node.js + Bun based CLI that launches an agent core and a web/desktop UI in separate processes |
| Entry‑point | `replio` | `opencode` (CLI) or `opencode-ai` (npm) |
| Runtime dependencies | None beyond stdlib | Node.js + Bun, npm, optional desktop bundler |
| Deployment | Single binary, no daemon | CLI + optional desktop app; can run in Docker or via Homebrew/Scoop/Choco |
| Multi‑process | No | Yes (CLI + UI + optional desktop) |

## 3. Tooling & Function Calling

| Aspect | REPL.io | OpenCode |
|--------|---------|----------|
| Built‑in tools | web search, fetch page, file I/O, shell, permission gating | web search, fetch page, file I/O, shell, Git, Docker, npm, etc. (rich toolset) |
| Permission model | Path‑scoped `allow/ask/deny` with runtime prompts | `build` agent has full access, `plan` agent is read‑only; permissions requested at runtime |
| Function‑calling scheme | OpenAI‑compatible JSON schema | OpenAI‑compatible JSON schema |
| Extensibility | Python plugins via a simple registry | NPM packages and a plugin SDK (`opencode-plugin`) for custom tools, agents, UI extensions |

## 4. Channels & UI

| Feature | REPL.io | OpenCode |
|---------|---------|----------|
| Built‑in UI | Terminal REPL only | Terminal UI (rich TUI), optional desktop app (Electron‑like) |
| Messaging channels | None | None (CLI/desktop only) |
| Web UI | None | None (but a desktop wrapper is available) |
| TUI | Basic REPL | Advanced TUI with panel layout, code preview, diff view |

## 5. Provider & Model Support

| Aspect | REPL.io | OpenCode |
|--------|---------|----------|
| LLM providers | OpenAI (default) | OpenAI, Anthropic, Gemini, local via Ollama (via `opencode-ai` provider config) |
| Local model support | Not built‑in (requires custom provider) | Built‑in local model support via `opencode-ai` provider abstraction |

## 6. Persistence & Telemetry

| Feature | REPL.io | OpenCode |
|---------|---------|----------|
| Session persistence | Append‑only JSON logs, compaction | Telemetry contracts (OpenCode uses a custom telemetry schema), logs in `~/.opencode/logs` |
| State management | Simple conversation context | Agent context stack; multi‑agent workflow (build, plan, general) |
| Telemetry | None | Vendor‑neutral telemetry contracts, optional integration with external telemetry backends |

## 7. Security & Isolation

| Project | Default isolation | Sandbox options | Notes |
|---------|-------------------|----------------|-------|
| REPL.io | Runs with user permissions; permission prompts per path | No OS sandboxing; relies on permission prompts | Minimal security guarantees |
| OpenCode | Runs with user permissions; `plan` agent is read‑only |
|  | Docker, micro‑VM via `opencode-ai`, optional policy sandboxing | Stronger isolation via containerization; desktop app runs in a sandboxed environment |

## 8. Community & Ecosystem

| Project | License | Community | Plugin Ecosystem | Docs |
|---------|---------|-----------|-----------------|------|
| REPL.io | MIT | Small, GitHub‑centric | Python plugins | Docs in repo; minimal |
| OpenCode | MIT | Active on GitHub, Discord, X | NPM packages; plugin SDK | Docs on opencode.ai; extensive developer guide |

## 9. When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a lightweight REPL with zero external dependencies that you can embed or expose via a tiny HTTP API | REPL.io | Minimal Python runtime, no OS dependencies |
| You want a full‑featured AI coding agent with a rich terminal UI and optional desktop application, and you’re comfortable with Node.js | OpenCode | Rich toolset, multi‑agent workflow, desktop app, advanced UI |
| You want strong isolation out of the box | OpenCode (via Docker or micro‑VM) | Built‑in docs for containerization and sandboxing |

## 10. Summary Table

| Feature | REPL.io | OpenCode |
|---------|---------|----------|
| Language | Python | TypeScript/JS + Bun |
| Runtime | Single process | CLI + UI + optional desktop |
| Extensibility | Python plugins | NPM plugin SDK |
| Channels | None | None (CLI/desktop only) |
| LLM providers | OpenAI (default) | OpenAI, Anthropic, Gemini, local via Ollama |
| UI | Terminal REPL | Terminal UI + desktop app |
| Persistence | JSON logs | Telemetry contracts & logs |
| Isolation | Permissions prompts | Docker / micro‑VM |
| Use case | Quick REPL & HTTP API | Full‑featured coding agent with UI |

## 11. References

- REPL.io: https://github.com/emyasnikov/replio
- OpenCode: https://github.com/anomalyco/opencode
- OpenCode Docs: https://opencode.ai/docs
- REPL.io Docs: https://github.com/emyasnikov/replio/tree/main/docs
