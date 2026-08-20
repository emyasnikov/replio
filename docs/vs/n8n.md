# Replio vs. n8n

This document compares **Replio** (github.com/emyasnikov/replio) and **n8n** (github.com/n8n-io/n8n). n8n is a fair-code workflow automation platform with native AI capabilities; Replio is a minimal terminal agent core. Beyond both being agent-capable, they target very different users - Replio is a code-first developer tool and n8n is a broad integration/automation platform with a visual canvas.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| n8n | TypeScript | https://github.com/n8n-io/n8n | Fair-code (Sustainable Use License) | Visual workflow automation and AI agent platform with 1500+ integrations |

n8n is fair-code, not MIT - the source is available and self-hostable, but a separate n8n Enterprise License covers additional features.

## Architecture & Runtime Model

| Feature | Replio | n8n |
|---------|--------|-----|
| What it is | A terminal agent application | A self-hosted/cloud automation platform with a visual editor |
| Core model | Single streaming agent loop per turn | Node-based workflows connecting triggers, apps, and AI agents |
| Entry point | `replio` (REPL), `replio run`, `replio serve` | Web editor on `localhost:5678`, `npx n8n`, or Docker |
| Building style | Code and slash commands | Visual canvas; custom code in JavaScript, Python, or npm packages |
| Dependencies | None beyond stdlib | Node.js, large platform with many integrations |

## Capabilities

| Feature | Replio | n8n |
|---------|--------|-----|
| Workflow automation | Shell/script level only | Broad: triggers, schedules, webhooks, and 1500+ integrations |
| AI agents | Model tool-calling loop | Build multi-step AI agents with tools, logic, and human approvals |
| Integrations | Web search, files, shell | Extensive: apps (Slack, Gmail...), databases, and APIs |
| MCP | Client and server via bundled plugin | Both an MCP client and MCP server |
| Templates | None | 9000+ workflow templates |
| Model flexibility | Multi-provider + local via Ollama | OpenAI, Anthropic, Google, open-source models, no lock-in |

## Channels & UI

| Feature | Replio | n8n |
|---------|--------|-----|
| Built-in UI | Terminal REPL | Visual workflow editor (web) |
| API | `replio serve` HTTP JSON API | Full platform API, webhooks, and nodes |
| Target user | Developers and CI | Builders, integrators, and operations teams |

## Security & Operations

| Feature | Replio | n8n |
|---------|--------|-----|
| Deployment | Local process or `serve` | Self-host (npm/Docker) or n8n Cloud |
| Enterprise features | None | Role-based access control, audit trails, enterprise edition |
| Default isolation | Runs with user permissions; path-scoped prompts | Runs with configured permissions; human-approval steps in workflows |

## Community & Ecosystem

| Project | License | Community | Ecosystem | Docs |
|---------|---------|-----------|-----------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| n8n | Fair-code | Large, very active | 1500+ integrations, template library, forum | docs.n8n.io, extensive |

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You want a minimal, MIT-licensed terminal agent core to script or expose via HTTP | Replio | Zero-dep stdlib Python, code-first |
| You want to automate business workflows across many apps with a visual editor | n8n | 1500+ integrations, triggers, templates |
| You want AI agents wired into your existing app ecosystem | n8n | Native AI nodes over a broad integration surface |

## Summary Table

| Feature | Replio | n8n |
|---------|--------|-----|
| Type | Terminal agent core | Workflow automation + AI agent platform |
| Language | Python (stdlib) | TypeScript |
| License | MIT | Fair-code (Sustainable Use) |
| Building style | Code / commands | Visual canvas + custom code |
| Integrations | Web, files, shell | 1500+ |
| UI | Terminal REPL | Web editor |
| Use case | Turn-key terminal agent | Broad workflow and AI automation |

## References

- https://docs.n8n.io
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/n8n-io/n8n
