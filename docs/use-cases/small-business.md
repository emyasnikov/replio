# Small business & solo operators

Small companies get the same core properties an enterprise pays a lot for - complete audit logging, data on your own machine, no vendor lock-in - at near-zero cost and with no IT department. A few-megabyte process runs on the office PC or one small server and serves the whole team over the HTTP API. The shared foundation - what Replio provides today, the adoption path, and the reference architecture - is in [index.md](index.md).

## Why it fits

- **Enterprise-grade logging for free** - every session records messages, tool calls, results, and reasoning. For a small manufacturer that is a ready-made quality and decision trail without buying a QMS.
- **No lock-in, no licensing burden** - zero external dependencies, a MIT core, and any OpenAI-compatible provider (or a local model). You are never paying per seat or chained to a vendor's pricing page.
- **Runs on what you have** - one existing machine hosts the agent. Team members reach it through `replio serve` (`POST /chat`, `GET /sessions`) or through the REPL on their own desks.
- **Scope by folder, not by headcount** - one agent per function (quality, production, service, admin), each pinned to its own directory and tool set. That discipline replaces a lot of permission admin.

## Fit by use case

- **Small manufacturers and workshops** - quality documentation, layered process audit (LPA) checklists, batch and deviation records, work instructions searchable in plain language. The audit-first design in [enterprise.md](enterprise.md) applies at whatever scale you run: start read-only, gate any write.
- **Service businesses** - recurring client reports, job summaries, and documentation drafted from your own records, with sources cited. `replio run` schedules these headlessly (cron-friendly) so reporting stops eating the week.
- **Consultants and solo operators** - research, proposal and deliverable drafting, and a complete client-facing paper trail. Sessions double as the project history you can hand over.
- **Startups** - internal knowledge, onboarding docs, support and release notes generated from the codebase and history. The developer guide covers team-specific patterns: [developer.md](developer.md).
- **Back office** - admin queries against spreadsheets and documents, standard letters, and filing summaries. Write actions stay human-approved.

## Gaps and planned

Connectors to typical small-business systems are future work: spreadsheet and CSV querying, POS / invoicing integrations, and lightweight document management. These track the roadmap in [TODO.md](../../TODO.md). Deployment guidance for a single machine is in [docs/deploy.md](../deploy.md).

## Get started

1. Install once on the office machine: `pip install replio`, then run `replio serve --path .replio` (or your work directory) and `replio plugins install` for any plugin the business needs.
2. `/connect` to a provider - a hosted OpenAI-compatible endpoint for convenience, or Ollama for a fully on-premise setup.
3. Lock permissions down: `tool_permission.bash: ask` (the default), `tools.deny` anything unused, and keep write tools out of read-only agents.
4. Point people at the API or a REPL session. Every question and every answer is on the record in `.replio/sessions/`.
