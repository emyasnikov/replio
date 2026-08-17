# Enterprise fit

Replio is deliberately small: a zero-dependency agentic core with one streaming loop, scoped per-process agents, and an append-only session log. That makes it a strong **orchestration, analysis, and assistant layer** above existing systems - not a replacement for the deterministic systems that run production (SCADA, PLC, MES, ERP, quality and maintenance systems). The recurring conclusion across the research is consistent: start read-only, keep humans in the loop for anything that writes or controls, and grow autonomy in bounded steps.

## What Replio provides today

The following capabilities exist now and are the foundation an enterprise evaluation builds on:

- **Auditability by design** - every session is a complete, append-only log. Each message, tool call and its result, reasoning (`thinking`), and error is persisted with timestamps, duration, model, and provider. Entries are never removed. Compaction only trims the provider context, never the log. See the session format in [docs/session.md](session.md).
- **Zero-dependency core** - Python standard library only. Nothing to audit, no supply chain, no lockfile churn. In a regulated environment this is a supply-chain and security property, not just a convenience.
- **Local-first data sovereignty** - config and session logs live on your disk. All provider traffic is outbound. No external logging or telemetry service holds enterprise data. Data stays on company infrastructure.
- **Permissions and isolation** - every tool is gated by `allow` / `ask` / `deny`, with path-scoped confirmations for anything outside an agent's worktree. Headless agents auto-deny anything that would require confirmation, so an agent's reachable surface is exactly what its config allows.
- **Fleet shape** - one process per single-purpose agent, each scoped to its own folder, config, model, and tool permissions. A few megabytes per process, so dozens or hundreds of focused agents fit on one machine. See [docs/fleet.md](fleet.md).
- **Headless modes** - `replio run` for scripting and CI/CD, `replio serve` for an HTTP JSON API (`POST /chat`, `GET /sessions`, `GET /health`, `GET /version`). Agents talk to each other over the same API.
- **Plugin-first extensibility** - external repositories register tools, providers, commands, and services without touching the core. Plugin dependencies are imported lazily, so the stdlib-only guarantee holds. See [docs/plugins.md](plugins.md).
- **Multi-provider** - Ollama, OpenAI, Groq, Anthropic, and any OpenAI-compatible endpoint, with auto-detection from the base URL. Local models keep confidential data in-house.

## Fit by capability area

The research consistently ranks the capability areas in the same order. This table generalizes that ranking beyond food production.

| Area | Fit | Notes |
|------|-----|-------|
| Monitoring | High | Summarizing alarms and context, correlating data sources, explaining deviations. Read-only, low risk. Needs data-source connectors. |
| Analysis | High | Root-cause analysis, trends, comparisons, KPI breakdowns. Keep deterministic calculation (SQL, time-series math, OEE formulas) in the analytics layer and use the LLM for interpretation. |
| Reporting | High | Shift/day/week reports, deviation reports, management summaries. Requires structured data, source and time-range citation, and data completeness indicators. |
| Planning | Medium | Drafting and evaluating plan variants, spotting capacity conflicts. The actual optimization belongs in a deterministic solver or APS/MES system. |
| Control / writing actions | Low to medium | Creating non-critical tickets or work orders with approval. Never direct control of safety-critical loops. Write actions must go through a permission, policy, and approval chain. |

The guiding principle from the research applies across industries: the target architecture is not "the model operates the plant" but "the agent interprets data and proposes actions, a policy and workflow layer checks them, and only a limited gateway may execute approved commands."

## Industry fits

Replio's combination of auditability, local control, and low footprint applies broadly across manufacturing and operations. The verticals below are examples of where the fit is strongest. The food section is the researched reference case.

### Manufacturing (general)

- **Document and knowledge access** - SOPs, work instructions, specifications, and standards searchable in plain language, with the current and valid version surfaced and cited.
- **Operations reporting** - automated shift, day, and deviation reports across lines, plants, and sites.
- **Maintenance support** - fault analysis against asset history, drafting work orders, spare-part queries. With CMMS integration, preparing and (with approval) raising work orders.
- **Production analysis** - OEE, downtime, scrap, and energy analysis, capacity and bottleneck questions in natural language.
- **Planning assistance** - plan variants, conflict detection, what-if scenarios for delays or outages.

### Food & beverage

The food industry is highly regulated (HACCP, IFS Food, BRCGS, ISO 22000, EU Regulation 178/2002) and requires full traceability of every decision. That is precisely where Replio's audit-first design pays off:

- **HACCP / CCP monitoring** - continuously watch critical control points (core temperatures, pasteurization, cold chain) and alert on deviation with a root-cause explanation.
- **Batch traceability** - follow lots from raw material to finished product, identify affected batches, and prepare recall documentation.
- **Compliance reporting** - automated documentation for audits: hygiene training, cleaning confirmations, quality releases, deviation records.
- **Recipe and allergen management** - versioned recipes, allergen cross-contamination risk awareness in line sequencing and cleaning cycles.
- **Supplier and quality scorecards** - aggregate quality data, delivery reliability, and complaint rates.

As elsewhere, food safety decisions (release of a batch, recall, setpoint changes) must stay human-gated. The agent prepares and evidences them.

### Pharmaceuticals & life sciences

Same pattern as food but with even tighter validation requirements (GxP, 21 CFR Part 11, EU Annex 11): audit trails, electronic records, batch records, and deviation management. Replio's complete session logs and local storage align with validated-environment expectations, and the same phased approach applies - document knowledge, monitoring explanation, deviation analysis, and audit-ready reporting before any write access.

### Chemicals & process industries

Continuous process data, alarm floods, energy and media consumption, safety documentation (SDS, permit-to-work), and regulatory reporting. Read-only alarm triage and root-cause analysis are the natural entry points. Any setpoint or valve action belongs behind a dedicated gateway with independent safety functions.

### Automotive & discrete manufacturing

Line-side quality, andon/poka-yoke deviations, supplier quality, maintenance and tooling management, and production planning across variants. High value in reporting and analysis. Control stays with the PLC / line control layer.

### Logistics & supply chain

Shipment monitoring, exception handling, carrier scorecards, warehouse querying, and documentation. Natural home for reporting and alerting. Write actions (order changes, dispatch instructions) need approval workflows.

### Energy & utilities

Asset monitoring, anomaly and predictive maintenance on rotating equipment, outage documentation, and regulatory reporting. Read-only insight and reporting first. Grid- or plant-critical actions remain with the control systems.

### Finance & healthcare (support functions)

Less directly an industrial control use case, but the same core applies to auditable assistants for regulated back-office work: document knowledge, report generation, and compliance-adjacent drafting where every step is logged.

## Enterprise extensions needed

The research and the roadmap ([TODO.md](../TODO.md)) agree on what an enterprise deployment adds on top of the core. These are planned or required extensions, not current capabilities:

- **Identity and access** - OIDC / SAML / LDAP integration, role-based access control down to tool level, tenant and site separation.
- **MCP support** - an MCP client plugin (connect to external MCP servers and register their tools into the ToolRegistry) and an MCP server (expose Replio's tools and sessions to external agents). Planned in [TODO.md](../TODO.md).
- **Connectors** - data ingestion and write channels for the systems of record: OPC UA / MQTT for machine and sensor data, and adapters for MES, ERP, LIMS, CMMS, WMS, and document management. The enterprise plugin list in [TODO.md](../TODO.md) covers `read_stream`/`write_stream`, time-series analysis, model inference, scheduling optimization, SCADA commands, and reporting.
- **Tool gateway and policy engine** - a controlled layer between the agent and target systems: whitelisted tools, strict input schemas, read/write separation, value ranges, rate limits, idempotency, four-eyes approval, dry run, and full logging. Write tools must never carry the same rights as read tools.
- **Durable workflows** - retries with backoff, timeouts, resumability, dead-letter queues, scheduled jobs, and explicit human-in-the-loop steps with a status model (`proposed`, `approved`, `executing`, `verified`, `failed`). A chat loop alone is not a workflow engine.
- **Central audit aggregation** - Replio's per-agent session logs are complete, but enterprise compliance wants a central, tamper-evident view: aggregated audit with correlation IDs across agents and target systems, retention policies, and export for compliance and forensics. Options are a lightweight audit proxy in front of `replio serve`, or a dedicated store.
- **Observability** - metrics for latency, cost, errors, and tool usage, tracing across agent, MCP, and target systems, alerting on misbehavior, prompt and model versioning, rate and budget limits.
- **Edge deployment** - offline-capable agents with local buffering and store-and-forward for plants with limited or unreliable connectivity.
- **Sandboxed execution** - namespace/container isolation for `run_command`, listed as planned in [TODO.md](../TODO.md).

## Reference architecture

A production-grade deployment composes three layers. Replio is the agent runtime in the middle. Enterprise functions are separate services around it rather than logic baked into the core.

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
- **Fleet and swarm** - [fleet.md](fleet.md) and [swarm.md](swarm.md) describe the two composable layers: a fleet of scoped `replio serve` processes, and a swarm of cooperating agents (personas, `delegate`, auditors) that runs on top of the fleet or in-process. For enterprise use the research recommends a bounded, hierarchical multi-agent system - a coordinator delegating to specialized agents with clear responsibilities, minimal tool sets, and defined output formats - rather than a freely communicating swarm.
- **Human-in-the-loop** - write and control actions flow through `propose -> policy check -> human approval -> execute -> verify -> audit`, so "autonomous agents" become an auditable business process.

## Adoption roadmap

The same phased path recurs across the research and applies to any vertical:

1. **Read-only copilot** - document search, KPI queries, shift and day reporting, alarm and fault analysis. Success criteria: faster reporting, traceable sources, no write access to production systems.
2. **Workflow assistant** - draft tickets and work orders, prepare deviation records, create plan variants, trigger notifications. All writes require user approval.
3. **Bounded autonomy** - escalate defined alarms, raise work orders under safe criteria, propose batch holds, execute controlled non-safety-critical actions. Only after validation, and only through the tool gateway and policy engine.
4. **Fleet-wide platform** - fleet orchestration, unified connectors and agent packages, edge capability, cross-site benchmarks, central compliance and audit evaluation.

## Audit advantage vs. alternatives

The research positions Replio's audit capability as its main differentiator for regulated environments. The honest comparison is more nuanced than the headline claims in some of the research:

| Criterion | Replio today | OpenClaw (per its audit docs) |
|-----------|--------------|-------------------------------|
| Log granularity | Session-based: messages, tool calls, arguments, results, thinking, errors, timestamps, model | Gateway-wide: run identity, time, agent, action, status, result code |
| Tool arguments and context | Stored in the session log | Deliberately not stored in the audit ledger (metadata-only, privacy-friendly) |
| Reasoning | `thinking` metadata preserved with each assistant message | Not captured in the audit ledger |
| Tamper resistance | Append-only local files (modification is detectable, not cryptographically sealed) | Hash-chaining, optional SIEM forwarding |
| Cross-agent trail | Per-agent sessions, a supervisor must aggregate | Built-in gateway aggregation |
| Data sovereignty | Local files, no external service | Workspace-based, local-first by design |

Replio's advantage is not that it is inherently "more secure" - it is that its logs are **content-complete**: the full chain from user request, context, tool call with arguments, result, and reasoning is reconstructable, which is what auditors and quality departments actually need for batch-level traceability, deviation investigation, and recall documentation. That completeness is paired with strict isolation (worktree scoping, headless auto-deny) and zero external logging. For enterprise-grade compliance, the research recommends adding central aggregation and tamper-evidence (hash-chained logging or WORM storage) on top of the existing session logs - both are additive, not rework.
