# Vision

**One window to access and control all agents**

Replio is the single window to your agents. The main agent, **assistant**, is the point of contact: it greets you on first run and asks what you want to do, answers small tasks inline in the current run, delegates bigger tasks to sub-agents or whole teams instead of blocking, runs recurring work in the background, watches your other agents for health, and reports back. Everything you need to see - sessions, running agents, and configured jobs on the machine - is reachable from one place. Users never see the machinery. They feel supported and do less work.

## How the assistant works

- **Onboarding** - on first run the assistant introduces itself, explains what it can do, and asks what the user wants to do. No system-level configuration is required of simple users.
- **Small tasks inline** - a question or a small task is answered in the current run, through the existing one-stream agent loop.
- **Bigger tasks delegated, never blocking** - for work that does not end after one task, the assistant starts sub-agents or whole teams, then reports their status. The user can check status with commands, jump into a session, ask for the current state, or view and mark items done on a per-agent todo list.
- **Recurring tasks carry their own role** - each job carries its own type and skills, so behavior is encoded once instead of re-prompted. A recurring task that maintains docs "per AGENTS.md" keeps that convention in its own skill, not in every prompt.
- **Health monitoring** - the assistant can watch endpoints (for example the `/health` of agents running as web APIs) and warn when an agent stops responding.
- **One-window status** - sessions, running agents, and configured jobs on the current machine are visible with commands, without a separate CLI. Logs are reachable from the same surface.
- **Report-back** - finished or failed runs surface a summary, and are delivered out-of-band over connectors (email first, an idea, not yet built) when the terminal is closed.
- **Governance mode** - when needed, the full control surface is available. For small tasks the assistant simply responds in the current run. The user does not see the complexity of the whole, only the reduced workload.

## Decisions

- **Assistant is the single point of contact** - the main agent is named `assistant`. Delegation and team composition are assistant-driven, using the types, teams, and skills registries (bundled, global, local, and plugin layers).
- **Sequential-first** - team stages run one member after another via `run_subagent` (existing, battle-tested). No concurrency in the first iteration. In-process threaded concurrency is a later milestone (cuts wall-clock, not tokens).
- **No pre-saved run prompts** - briefs, handoff, and memory are generated per run. Stored artifacts are types, teams, and skills in the registries.
- **Cache model** - persistent member sessions for recurring teams (`job`-style warm sessions), shared team memory file, and per-run briefs carrying facts. One-off runs get fresh `sub_` sessions.
- **Core stays thin and publishable** - registries plus the sequential runner plus plugin hooks. Everything customer-specific lives in local `types.json`, `teams.json`, `skills/`, or plugins.

## Context economics (why this costs what it costs)

- Sub-engines are separate `Engine`s - no in-memory context sharing exists. The persistence channel is session + memory files.
- Cold starts cost: file re-reads by multiple members, brief duplication. Mitigations: facts-in-briefs (not just paths), research stages summarizing into team memory (`.replio/teams/<name>/memory.md`), recurring teams keep member sessions warm, one-off teams stay fresh and clean.
- Honest limit: per-run redundancy will not go to zero. Sequential wall-clock is accepted.

## Phases

The task mapping lives in `PLAN.md` (work packages). The phases below name the verifiable stages of the assistant track, ordered by dependency:

- **Onboarding** - the assistant introduces itself on first run and asks what to do. Defaults and docs for simple users.
- **One-window status** - `/status` shows sessions, running agents, and configured jobs on the machine. Logs are reachable from the same surface.
- **Non-blocking delegation** - the assistant delegates big tasks to sub-agents or teams without blocking, with progress reporting, jump-into-session, and per-agent todo lists that can be marked done.
- **Recurring tasks with roles** - jobs carry their own type and skills, so recurring behavior is encoded per task.
- **Health monitoring** - the assistant watches agent endpoints and warns on failures.
- **Report-back connectors** - job summaries delivered out-of-band (email first).
- **Governance mode** - the full control surface when needed, invisible otherwise.

## TODO.md placement

The assistant track is tracked as open tasks at the top of `TODO.md` (onboarding, one-window status, health monitoring, per-agent todo lists, non-blocking delegation, recurring tasks with roles, report-back connectors) and as work packages in `PLAN.md` (Control & governance, Delegation & swarm, Jobs operations + report-back).

## Out of scope (later milestones, listed not planned)

In-process threaded team concurrency and a live progress channel, war-room focus view, lead-grant approvals, generate > check > correct loop, fleet-backed teams, and report-back connectors beyond email.
