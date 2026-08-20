# Replio vs. Claude Code

This document compares two terminal AI coding agents: **Replio** (github.com/emyasnikov/replio) and **Claude Code** by Anthropic. Both run an agentic loop that reads code, calls tools, and edits files, but they sit at opposite ends of the openness and distribution spectrum - Replio is a minimal MIT-licensed core you control, while Claude Code is a highly integrated commercial product tied to Anthropic's Claude models.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| Claude Code | TypeScript | https://github.com/anthropics/claude-code | Source-available (commercial) | Agentic coding tool that reads codebases, edits files, runs commands, and integrates with dev tools |

Claude Code is a commercial product. It is not fully open source - the repository is source-available and a paid Claude subscription or Anthropic Console account is normally required.

## Architecture & Runtime Model

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Core runtime | Single Python process with a streaming agent loop | Node.js-based agent that shares one engine across surfaces |
| Front-ends | Terminal REPL, `replio run` (CLI), `replio serve` (HTTP JSON API) | Terminal CLI, VS Code, JetBrains, desktop app, web, mobile |
| Execution | Local tools invoked over the OpenAI-compatible loop | Reads the codebase, edits files, runs commands, uses Git (staging, branches, PRs) |
| Dependencies | None beyond stdlib | Node.js runtime, requires Claude subscription or API account |

## Tooling & Function Calling

| Aspect | Replio | Claude Code |
|--------|--------|-------------|
| Built-in tools | Web search, fetch page, file I/O, shell - via bundled plugin tools | Codebase search/read, file edit, shell, Git, plus MCP-connected tools |
| Tool ecosystem | Python plugin registry | MCP servers, skills, hooks, sub-agents, and the Agent SDK |
| Function-calling scheme | OpenAI-compatible JSON schema | Model/API-native function calling (Claude) |
| Extensibility | Plugins register tools/providers/commands | Skills, MCP, hooks, the Agent SDK for building custom agents |

## Channels & UI

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Built-in UI | Terminal REPL | Terminal, IDE (VS Code/JetBrains), desktop app, web |
| Remote access | None | Web, mobile, Remote Control, `--teleport`, Channels (Telegram, Discord), Slack |
| Scheduling | None | Cloud Routines, desktop scheduled tasks, `/loop` |
| CI/CD | `replio run` for scripting | `claude -p` print mode, GitHub Actions, GitLab CI/CD |

## Provider & Model Support

| Aspect | Replio | Claude Code |
|--------|--------|-------------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, any OpenAI-compatible endpoint | Primarily Claude via subscription/API, with third-party providers supported on terminal and VS Code |
| Local models | Via Ollama | Third-party/OpenAI-compatible providers on some surfaces |

## Persistence & Memory

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Session persistence | Append-only JSON session logs with compaction | Session history across surfaces, plus `CLAUDE.md` project instructions |
| Memory | None (per-session context) | Auto memory that saves learnings across sessions, plus skills |

## Security & Isolation

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Default isolation | Runs with user permissions | Runs with user permissions, with permission modes gating edits and shell commands |
| Permission model | Path-scoped `allow`/`ask`/`deny` prompts | Permission controls for file edits and command execution, plus hooks for lifecycle safety |

Both rely on permission prompts rather than a sandbox by default.

## Community & Ecosystem

| Project | License | Community | Ecosystem | Docs |
|---------|---------|-----------|-----------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| Claude Code | Source-available | Large, backed by Anthropic | MCP server ecosystem, skills hub | code.claude.com/docs, extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You need a minimal, MIT-licensed agent core you own and can embed, script, or expose via HTTP | Replio | Zero-dep stdlib Python, no subscription |
| You want a polished coding agent tightly integrated with Claude, IDEs, CI, and messaging | Claude Code | Rich surface coverage, MCP, sub-agents, scheduling |
| You want full multi-provider and local-model flexibility with no lock-in | Replio | Bring any OpenAI-compatible model including local |

## Summary Table

| Feature | Replio | Claude Code |
|---------|--------|-------------|
| Language | Python (stdlib) | TypeScript |
| License | MIT (open) | Source-available (commercial) |
| Runtime | Single process | Agent engine across many surfaces |
| Providers | Multi-provider incl. local | Claude-first |
| Channels | Terminal only | Terminal, IDE, desktop, web, messaging |
| Extensibility | Python plugins | MCP, skills, hooks, Agent SDK |
| Use case | Minimal embeddable agent core | Integrated commercial coding agent |

## References

- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/anthropics/claude-code
- https://code.claude.com/docs
