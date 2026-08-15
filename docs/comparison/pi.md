# REPL.io vs. Pi

This document compares the two open‑source personal AI assistant projects **REPL.io** and **Pi Agent Harness** (earendil‑works/pi).  The goal is to highlight key design choices, runtime models, and ecosystem differences.

## 1. Project Overview

| Project | Primary Language | Repo | License | Core
|---------|------------------|------|---------|------
| REPL.io | Python | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies
| Pi | TypeScript/JavaScript (Node + Bun) | https://github.com/earendil-works/pi | MIT | Monorepo with agent core, unified LLM API, coding‑agent CLI, telemetry, and TUI

## 2. Architecture & Runtime Model

| Feature | REPL.io | Pi
|---------|---------|----
| Core runtime | Single Python process with streaming loop | CLI that spawns the agent core in the same process
| Entry‑point | `replio` command | `pi` command
| Runtime dependencies | None beyond stdlib | Node.js + Bun, npm
| Deployment | Single binary, no daemon | CLI can run directly; builds standalone binaries for release
| Multi‑process | No | No, but monorepo can run services separately

### REPL.io
A tight‑coupled loop that handles REPL, CLI, and HTTP API. Tools are loaded lazily and can be extended by Python plugins.

### Pi
Monorepo architecture: `@earendil-works/pi-agent-core` provides the agent runtime, `@earendil-works/pi-ai` offers a unified LLM provider layer, and `@earendil-works/pi-coding-agent` ships an interactive CLI. The CLI runs the agent runtime in the same process.

## 3. Tooling & Function Calling

| Aspect | REPL.io | Pi
|--------|---------|----
| Built‑in tools | web search, fetch page, file I/O, shell, permission gating (`allow/ask/deny`) | web search, fetch page, file I/O, shell, and custom `!` command syntax
| Permission model | Path‑scoped `allow/ask/deny` with runtime prompts | No built‑in permission system; rely on OS sandboxing or Docker
| Function‑calling scheme | OpenAI‑compatible JSON schema | OpenAI‑compatible JSON schema
| Extensibility | Python plugins register tools via a simple registry | Packages expose `@tool`/`@skill` decorators; monorepo architecture

## 4. Channels & UI

| Feature | REPL.io | Pi
|---------|---------|----
| Built‑in UI | Terminal REPL only | Terminal UI library (`@earendil-works/pi-tui`), CLI only
| Messaging channels | None | None (CLI only)
| Web UI | None | None
| TUI | Yes (basic REPL) | Yes (differential rendering)

## 5. Provider & Model Support

| Aspect | REPL.io | Pi
|--------|---------|----
| LLM providers | OpenAI (default) | OpenAI, Anthropic, Google, etc. via unified API (`@earendil-works/pi-ai`)
| Local model support | Not built‑in (needs custom provider) | Built‑in local providers via `@earendil-works/pi-ai`

## 6. Persistence & Telemetry

| Feature | REPL.io | Pi
|---------|---------|----
| Session persistence | Append‑only JSON logs, compaction | Telemetry contracts (`@earendil-works/pi-telemetry`), logs in workspace
| State management | Simple conversation context | Agent runtime has state stack; supports structured conversation state
| Telemetry | None | Vendor‑neutral telemetry contracts, reference adapter, conformance tests

## 7. Security & Isolation

| Project | Default isolation | Sandbox options | Notes
|---------|-------------------|----------------|-------
| REPL.io | Runs with user permissions | Permission gating per path | No OS sandboxing; relies on prompts
| Pi | Runs with user permissions | Docker, micro‑VM (Gondolin), OpenShell policy sandbox | Recommendation to use containerization for stronger boundaries

## 8. Community & Ecosystem

| Project | License | Community | Plugin Ecosystem | Docs
|---------|---------|-----------|-----------------|------
| REPL.io | MIT | Small, GitHub‑centric | Python plugins | Docs in repo; minimal
| Pi | MIT | Active, GitHub + X | NPM packages in monorepo | Docs on pi.dev; extensive guide on containerization

## 9. When to Choose Which

| Scenario | Recommended Project | Why
|----------|---------------------|-----
| You need a lightweight, zero‑dependency REPL that can be embedded or exposed via a tiny HTTP API | REPL.io | Minimal Python runtime, no external deps
| You need a coding‑agent with a unified LLM API, telemetry, and the ability to build standalone binaries | Pi | Rich plugin ecosystem, telemetry support, ability to run as CLI or build standalone binaries
| You want strong isolation out of the box | Pi (via Docker or micro‑VM) | Built‑in docs for containerization

## 10. Summary Table

| Feature | REPL.io | Pi
|---------|---------|----
| Language | Python | TypeScript/JS + Bun
| Runtime | Single process | CLI + core runtime
| Extensibility | Python plugins | NPM packages in monorepo
| Channels | None | None (CLI only)
| LLM providers | OpenAI (default) | OpenAI, Anthropic, Google, etc.
| UI | Terminal REPL | Terminal TUI
| Persistence | JSON logs | Telemetry contracts
| Isolation | Permissions prompts | Docker / micro‑VM recommended
| Use case | Quick REPL & HTTP API | Coding agent with telemetry

## 11. References

- REPL.io: https://github.com/emyasnikov/replio
- Pi: https://github.com/earendil-works/pi
- Pi docs: https://pi.dev/docs/latest
- REPL.io docs: https://github.com/emyasnikov/replio/tree/main/docs
