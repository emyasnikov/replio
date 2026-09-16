# Harness

An **agent harness** is the runtime that turns a language model into an agent that can act: the execution loop, tool dispatch, context management, state and memory, permissions, and observability. You bring a model and instructions, and the harness runs the loop. This is the category Replio belongs to.

Harnesses differ in how much they ship and how they reach the user. Some are terminal coding agents, some are multi-channel gateways, and some are minimal runtimes you extend. Replio's angle is a zero-dependency core with orchestration built in: delegation, teams, scheduled jobs, and a fleet supervisor.

## Replio in this category

Replio is a harness that ships a complete loop with orchestration built in. One streaming loop powers a REPL, a CLI, and an HTTP API. Types and the `delegate` and `team` tools run sub-agents in process, jobs run scheduled durable work, and the fleet supervisor runs many scoped agents. The whole runtime is Python standard library only, so it is small and auditable, and it runs on low-resource hardware.

Choose Replio when you want a small, auditable runtime you own, many scoped agents under one supervisor, built-in scheduling and delegation, or an agent embedded in scripts and services.

## Representatives

Representatives with a full comparison below: Aider, Claude Code, Cline, Codex, Hermes, OpenClaw, OpenCode, OpenHands, Pi. `replio` is the reference column.

| Project | Language | License | Native tools | Multi-agent | Scheduling | Channels |
|---------|----------|---------|--------------|-------------|------------|----------|
| Aider | Python | Apache-2.0 | File edit, git-native | No | No | Terminal |
| Claude Code | TypeScript | Source-available (commercial) | Read, write, edit, bash, web | Subagents | Routines, desktop tasks | Terminal, IDE, desktop, web, mobile |
| Cline | TypeScript | Apache-2.0 | Plan/Act, checkpoints | Kanban parallel agents | No | IDE, CLI, SDK |
| Codex | Rust | Apache-2.0 | Terminal-native, sandboxed exec | Limited | No | Terminal, cloud |
| Hermes | Python + Node.js | Open source | 40+ tools, memory, skills | Isolated subagents | Cron with delivery | 7 messaging channels, desktop, web |
| OpenClaw | TypeScript | Open source | Gateway tools, browser | ACP child sessions | Cron tools | 29 messaging channels, web UI |
| OpenCode | TypeScript + Bun | Open source | File, bash, glob/grep, MCP | Child sessions (opt-in) | No | Terminal, desktop, IDE |
| OpenHands | Python | MIT | 25+ tools, apply_patch | Parallel conversation trees | No | Web UI, CLI |
| Pi | TypeScript + Bun | MIT | read, write, edit, bash | Extensions | No | Terminal |
| Replio | Python (stdlib only) | MIT | Web, file, edit, git, shell, dev wrappers | Types, delegate, teams, fleet | Jobs (cron/interval/one-shot) | Terminal, CLI, HTTP API, MCP |

## Profiles

### Aider
A terminal pair-programming agent with a git-native workflow: it maps the repository with tree-sitter, edits files, and auto-commits every change. It is a focused coding tool rather than a general orchestration runtime, with no scheduling, fleet, or multi-agent layer.

### Claude Code
Anthropic's commercial, source-available coding agent shared across terminal, IDE, desktop, web, and mobile surfaces. It has subagents, skills, hooks, MCP, and auto memory, and is Claude-first with a paid subscription. Replio trades that surface breadth for a zero-dependency, provider-agnostic core.

### Cline
An IDE extension, CLI, and SDK with a plan/act split, checkpoints, and a Kanban view for parallel agents. It is optimized for editor-centric coding with many providers. Replio targets fleets of scoped processes rather than one editor session.

### Codex
OpenAI's Rust coding agent with terminal-native and cloud surfaces, sandboxed execution, and MCP. It is tied to OpenAI models and ChatGPT plans. Replio is provider-agnostic and local-first.

### Hermes
Nous Research's self-improving personal agent with persistent memory, a skill learning loop, multi-channel messaging, and remote or serverless execution backends. It is a broad personal assistant. Replio is a stateless core that logs everything and orchestrates, without a learning loop.

### OpenClaw
A self-hosted TypeScript gateway that connects many messaging channels to agents and delegates coding to external harnesses. It is the multi-channel counterweight to a native core. Replio implements the loop and tools itself and reaches the user through terminal, CLI, and HTTP.

### OpenCode
A full-featured open-source coding agent with a rich TUI, desktop and IDE surfaces, many providers, and a plugin SDK. It is a coding-platform first. Replio is smaller and adds scheduling, fleet supervision, and in-process delegation.

### OpenHands
A Python software-engineering agent with Docker or Apptainer sandboxing, a web UI, and parallel conversation trees. It offers stronger isolation out of the box. Replio offers a smaller stdlib runtime and fleet orchestration instead.

### Pi
A minimal, self-extensible TypeScript harness with a unified LLM API, a TUI library, telemetry, and standalone binaries. It deliberately omits sub-agents, plan mode, and permission gates by default, leaving them to extensions. Replio ships orchestration and permissions in the core.

## When to choose

| Scenario | Pick | Why |
|----------|------|-----|
| A small, auditable, zero-dependency core you own and embed | Replio | Stdlib-only Python, REPL, CLI, and HTTP API from one loop |
| Many scoped agents under one supervisor, with scheduling | Replio | Fleet supervisor, jobs, and teams built in |
| A polished coding agent across IDE, desktop, and web | Claude Code, OpenCode, Cline | Rich surfaces and editor integration |
| An always-on assistant reachable from messaging apps | OpenClaw, Hermes | Multi-channel gateways and companion apps |
| A memory and skill learning loop that improves over time | Hermes | Persistent memory, skills, and a user model |
| Strong isolation with a working sandbox out of the box | OpenHands, Hermes, Pi | Container or micro-VM backends |
| A minimal runtime you extend with packages | Pi | Everything is an extension |

## Sources and evidence

Replio facts come from this repository (`README.md`, `docs/`). Competitor facts come from each project's public documentation and repository, and are summarized here at a level intended to stay stable. Numeric benchmarks are not included in this file. Any performance or resource claim belongs in a measured, dated benchmark, not a comparison page.

## References

- https://aider.chat
- https://github.com/anomalyco/opencode
- https://github.com/cline/cline
- https://github.com/earendil-works/pi
- https://github.com/emyasnikov/replio
- https://github.com/openai/codex
- https://github.com/openclaw/openclaw
- https://github.com/NousResearch/hermes-agent
- https://github.com/All-Hands-AI/OpenHands
- https://github.com/anthropics/claude-code
