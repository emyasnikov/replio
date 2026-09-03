# Use cases

Replio is deliberately small: a zero-dependency agentic core with one streaming loop, scoped per-process agents, and an append-only session log. That makes it a strong orchestration, analysis, and assistant layer above existing systems - not a replacement for the deterministic systems that run production (SCADA, PLC, MES, ERP, quality and maintenance systems). The recurring conclusion across the research is consistent: start read-only, keep humans in the loop for anything that writes or controls, and grow autonomy in bounded steps.

The use-case guides in this folder assess how that core fits a specific audience or context: [enterprise.md](enterprise.md), [personal.md](personal.md), [small-business.md](small-business.md), [developer.md](developer.md), [research.md](research.md), [education.md](education.md), and [homelab.md](homelab.md). This page holds the shared foundation they all build on.

## What Replio provides today

The following capabilities exist now and are the foundation any evaluation builds on:

- **Auditability by design** - every session is a complete, append-only log. Each message, tool call and its result, reasoning (`thinking`), and error is persisted with timestamps, duration, model, and provider, and every tool permission decision is recorded in the session `permissions` array. Entries are never removed. Compaction only trims the provider context, never the log. See the session format in [docs/session.md](../session.md).
- **Zero-dependency core** - Python standard library only. Nothing to audit, no supply chain, no lockfile churn. In a regulated environment this is a supply-chain and security property, not just a convenience.
- **Local-first data sovereignty** - config and session logs live on your disk. All provider traffic is outbound. No external logging or telemetry service holds your data. Data stays on your infrastructure.
- **Permissions and isolation** - every tool is gated by `allow` / `ask` / `deny`, with path-scoped confirmations for anything outside an agent's worktree. Headless agents auto-deny anything that would require confirmation, so an agent's reachable surface is exactly what its config allows.
- **Fleet shape** - one process per single-purpose agent, each scoped to its own folder, config, model, and tool permissions. A few megabytes per process, so dozens or hundreds of focused agents fit on one machine. See [docs/fleet.md](../fleet.md).
- **Headless modes** - `replio run` for scripting and CI/CD, `replio serve` for an HTTP JSON API (`POST /chat`, `GET /sessions`, `GET /health`, `GET /version`). Agents talk to each other over the same API.
- **Plugin-first extensibility** - external repositories register tools, providers, commands, and services without touching the core. Plugin dependencies are imported lazily, so the stdlib-only guarantee holds. See [docs/plugins.md](../plugins.md).
- **Multi-provider** - Ollama, OpenAI, Groq, Anthropic, and any OpenAI-compatible endpoint, with auto-detection from the base URL. Local models keep confidential data in-house.

## Adoption path

The same phased path recurs across the research and applies to any context, from a single personal machine to a regulated plant:

1. **Read-only copilot** - document search, KPI queries, shift and day reporting, alarm and fault analysis. Success criteria: faster reporting, traceable sources, no write access to target systems.
2. **Workflow assistant** - draft tickets and work orders, prepare deviation records, create plan variants, trigger notifications. All writes require user approval.
3. **Bounded autonomy** - escalate defined alarms, raise work orders under safe criteria, propose batch holds, execute controlled non-safety-critical actions. Only after validation, and only through a permission and approval chain.
4. **Fleet-wide platform** - fleet orchestration, unified connectors and agent packages, edge capability, cross-site benchmarks, central compliance and audit evaluation.

## Reference architecture

A production-grade deployment composes three layers. Replio is the agent runtime in the middle. Enterprise functions are separate services around it rather than logic baked into the core. Smaller deployments skip most of this and run one or a few agents.

```text
Users / shift lead / web / TUI / API
                 |
        Identity & Policy Layer
                 |
        Replio Control Plane
   Sessions | Agents | Approvals | Audit
                 |
       Agent Orchestrator / Workflow
                 |
        Tool Gateway / MCP Gateway
                 |
  ----------------------------------------
  MES | ERP | SCADA | Historian | LIMS
  CMMS | DMS | Monitoring | Planning
  ----------------------------------------
                 |
        Event Bus and Data Platform
                 |
      Edge Nodes / Plant Gateways
```

- **Control plane** - agents, configuration, policies, tool approvals, versions, deployments. Agents must never be able to change their own configuration, permissions, or tool list.
- **Data plane** - production data, documents, events, tool execution, and local connectors.
- **Fleet and swarm** - [fleet.md](../fleet.md) and [swarm.md](../swarm.md) describe the two composable layers: a fleet of scoped `replio serve` processes, and a swarm of cooperating agents (types, `delegate`, auditors) that runs on top of the fleet or in-process. For enterprise use the research recommends a bounded, hierarchical multi-agent system - a coordinator delegating to specialized agents with clear responsibilities, minimal tool sets, and defined output formats - rather than a freely communicating swarm.
- **Human-in-the-loop** - write and control actions flow through `propose -> policy check -> human approval -> execute -> verify -> audit`, so "autonomous agents" become an auditable business process.

## The use-case guides

- [Enterprise](enterprise.md) - regulated industries, industry fits, extension requirements, audit advantage
- [Personal](personal.md) - private and personal use, local models, privacy-first
- [Small business](small-business.md) - small companies, solo operators, and startups
- [Developer](developer.md) - coding assistants and engineering teams
- [Research](research.md) - academia and sensitive research data
- [Education](education.md) - teaching, tutoring, and course preparation
- [Home lab](homelab.md) - makers, self-hosters, and personal servers
