# Agent swarms

A swarm is the layer of agent cooperation. A fleet is many scoped processes running side by side, and a swarm is those processes or in-process engines working together on a task. A lead agent delegates subtasks to specialized sub-agents, auditors review the output, and the group iterates until the goal is met. Fleet and swarm orchestration are two layers, not two names for one thing.

| | Fleet orchestration | Swarm orchestration |
|---|---|---|
| Concern | Running agents | Making agents cooperate |
| Unit | `replio serve` process scoped to a folder | Agent with an agent type, either a fleet process or an in-process engine |
| Primitives | Supervisor with port allocation, health checks, restart policy, config generation | `/agent` types, `delegate` tool, sub-agent loops, auditor agents |
| Channel | None | `POST /chat` (cross-process) or an in-process sub-engine |
| Question | How do I keep the agents alive? | How do the agents get the job done? |

The two compose. A swarm can run on top of a fleet, each swarm agent a fleet process and `delegate` routing over the same `POST /chat` API. Delegation also works in-process as a sub-`Engine` with no fleet at all. The two tasks are therefore separable, and neither is subordinate to the other. See [fleet.md](fleet.md) for the fleet side.

## Building blocks

- **Agent types** (`/agent`): per-agent system prompt, session namespace, and optional model override. A type makes a sub-agent specialized instead of a copy of the caller. Per-agent permission profiles build on this.
- **`delegate(type, task)` tool**: spawns a sub-agent loop that runs a task with its own type, session, and model, and returns the result. The core swarm primitive.
- **Auditor agents**: sub-agents that review a produced output (tests, code review, fact-checking) instead of producing content themselves.
- **Generate to check to correct**: run a main agent, an auditor, and a fix pass in a loop until the auditor passes.
- **PM/dev/tester orchestration**: multiple specialized agents cooperating on one outcome as a user-facing pattern.

## Agent types and delegation

Agent types are named agent definitions - a system prompt, optional model override, and optional per-agent tool permissions - stored in a single JSON catalog with bundled, global, and local layers (schema, permission rule, and bundled default roster in [types.md](types.md)). `delegate(type, task)` spawns a sub-agent that runs the task with the type's prompt, session, and model, and returns the result. Delegation resolves its permission from the selected type: a configured type uses its own `tool_permission` overrides (category `delegate` defaults to `allow`, so delegation runs without a prompt unless an agent type sets `ask`), while a temporary type created only for parallel work defaults to `deny` until opted in. The bundled catalog ships two pre-carved teams - `researcher`/`writer`/`referencer`/`editor` for documents and `planner`/`programmer`/`tester`/`code-reviewer` for programming - ready to delegate to out of the box.

so a sub-agent can never gain a permission the caller was not authorized to delegate. A type that sets `grant_permission` may hand down categories it does not use itself (a supervisor that denies `edit`/`bash` can still delegate them). Sub-agents run in `build` mode regardless of the caller's mode

A document pipeline is a typical use: a lead agent asks a `researcher` for findings, hands them to a `writer`, has a `referencer` collect citations into a `.bib` file, and runs an `editor` to check the result against the original prompt. This is team orchestration built on types and delegation. Named pipelines are stored as teams - ordered type chains with per-stage task hints and handoff notes, in a four-layer registry (bundled `writing`/`programming` rosters, plugin contributions, global/local `teams.json`, see [teams.md](teams.md)). `Engine.run_team` executes a team sequentially - per-run briefs built from the task, prior stage results, the shared team memory (`.replio/teams/<name>/memory.md`), and stage handoffs, with a rolling memory write after the run. A lead agent runs one with the core `team(name, task)` tool, and the operator with `/teams run <name> <task>`.

## In-process vs. cross-process

| | In-process | Cross-process |
|---|---|---|
| Unit | Sub-`Engine` in the same process | Another `replio serve` agent |
| Setup | Spawn a child engine with an agent type | Point `delegate` at a sibling agent's `POST /chat` |
| Isolation | Shares the caller's process | Process, worktree, and tool-policy boundaries (see fleet.md) |
| Uses | Auditors, quick subtasks, no fleet required | Team orchestration across scoped folders |

## Security

Sub-agents follow the same tool policy as any agent. In-process sub-engines share the caller's privileges. Cross-process delegation is confined by the target agent's own worktree and `tool_permission` config.