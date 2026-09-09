# Replio vs. Claude Code

This document compares two terminal AI coding agents: **Replio** (github.com/emyasnikov/replio) and **Claude Code** by Anthropic. Both run an agentic loop that reads code, calls tools, and edits files, but they sit at opposite ends of the openness and distribution spectrum: Replio is a minimal MIT-licensed core you control, while Claude Code is a highly integrated commercial product tied to Anthropic's Claude models.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Zero-dependency agentic core: REPL, CLI, HTTP API, types/teams delegation, jobs, fleet, MCP |
| Claude Code | TypeScript | https://github.com/anthropics/claude-code | Source-available (commercial) | Agentic coding tool that reads codebases, edits files, runs commands, and integrates with dev tools |

Claude Code is a commercial product. It is not fully open source: the repository is source-available, and a paid Claude subscription or Anthropic Console account is normally required.

## Runtime & Architecture

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Core runtime | Single Python process with a streaming agent loop | Node.js-based agent that shares one engine across surfaces |
| Surfaces | Terminal REPL, `replio run`, `replio serve` (HTTP JSON API) | Terminal CLI, Desktop app, VS Code, JetBrains, web, mobile |
| Execution | Local tools over the OpenAI-compatible loop | Reads the codebase, edits files, runs commands, uses Git, drives browsers, computer use on macOS |
| Dependencies | None beyond the Python >= 3.10 stdlib | Node.js runtime, Claude subscription or API account |

## Tools & Function Calling

| Aspect | Replio | Claude Code |
|--------|--------|-------------|
| Built-in tools | Web search/fetch, file read/write/list/glob/grep, file edit, git, shell, test/lint/format wrappers, ask, delegate | Read, write, edit, bash, glob, grep, web search/fetch, monitor, plus MCP-connected tools |
| Tool ecosystem | Python plugin registry | MCP servers, skills, hooks, subagents, plugins |
| Function-calling scheme | OpenAI-compatible JSON schema | Model-native function calling (Claude) |
| Extensibility | Plugins register tools, providers, commands, services, types, teams, skills | Skills, MCP, hooks, Agent SDK (Python and TypeScript) |

## Channels & UI

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Built-in UI | Terminal REPL | Terminal, IDE (VS Code/JetBrains), Desktop, web, mobile |
| Remote access | None | Remote Control (drive a local session from claude.ai/code or mobile), Dispatch (mobile to Desktop), `--teleport`, web sessions |
| Channels | None | Research preview channels push events from Telegram, Discord, iMessage. Slack team chat routes to PRs |
| Scheduling | Jobs (cron/interval/one-shot) with retries and approval | Routines and Desktop scheduled tasks |
| CI/CD | `replio run` for scripting | `claude -p` print mode, GitHub Actions, GitLab CI/CD |

## Providers & Models

| Aspect | Replio | Claude Code |
|--------|--------|-------------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, OpenCode Zen/Go, any OpenAI-compatible endpoint | Primarily Claude via subscription/API. Third-party providers (Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry) on CLI and VS Code |
| Local models | Via Ollama | Via third-party/OpenAI-compatible providers on some surfaces |

## Persistence & Memory

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Session persistence | Append-only JSON session logs with compaction | Session history across surfaces, plus `CLAUDE.md` project instructions |
| Memory | None (per-session context) | Auto memory that saves learnings across sessions, plus skills |
| MCP | Client and server via bundled plugin | MCP client with connectors UI and settings files |

## Security & Isolation

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Default isolation | Runs with user permissions | Runs with user permissions, with permission modes gating edits and shell commands |
| Permission model | Path-scoped `allow`/`ask`/`deny` prompts | Permission controls for file edits and command execution, hooks for lifecycle safety |
| Sandboxing | None | None by default. Web sessions run in Anthropic-managed sandboxes |

Both rely on permission prompts rather than a sandbox by default.

## Plugins & Docs

| Project | Plugin Ecosystem | Docs |
|---------|------------------|------|
| Replio | Directory plugins, bundled `replio-core-*` plugins, `/plugins` + `replio plugins` | Docs in repo (`docs/`), README |
| Claude Code | MCP server ecosystem, skills hub, hooks, plugins | code.claude.com/docs, extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a minimal, MIT-licensed agent core you own and can embed, script, or expose via HTTP | Replio | Zero-dep stdlib Python, no subscription |
| You want a polished coding agent tightly integrated with Claude, IDEs, CI, and messaging | Claude Code | Rich surface coverage, MCP, subagents, scheduling, remote control |
| You want full multi-provider and local-model flexibility with no lock-in | Replio | Bring any OpenAI-compatible model including local |

## Summary Table

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Language | Python (stdlib) | TypeScript |
| License | MIT (open) | Source-available (commercial) |
| Runtime | Single process | Agent engine across many surfaces |
| Providers | Multi-provider incl. local | Claude-first, third-party on some surfaces |
| Channels | Terminal, HTTP API | Terminal, IDE, desktop, web, mobile, messaging |
| Extensibility | Python plugins | MCP, skills, hooks, Agent SDK |
| Use case | Minimal embeddable agent core | Integrated commercial coding agent |

## References

- https://code.claude.com/docs
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/anthropics/claude-code
