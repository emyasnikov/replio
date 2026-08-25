# Agent swarms

A swarm is the layer of agent cooperation. A fleet is many scoped processes running side by side, and a swarm is those processes, or in-process engines, working together on a task. A lead agent delegates subtasks to specialized sub-agents, auditors review the output, and the group iterates until the goal is met.

Fleet and swarm orchestration are two layers, not two names for one thing.

| | Fleet orchestration | Swarm orchestration |
|---|---|---|
| Concern | Running agents | Making agents cooperate |
| Unit | `replio serve` process scoped to a folder | Agent with a persona, either a fleet process or an in-process engine |
| Primitives | Supervisor with port allocation, health checks, restart policy, config generation | `/agent` personas, `delegate` tool, sub-agent loops, auditor agents |
| Channel | None | `POST /chat` (cross-process) or an in-process sub-engine |
| Question | How do I keep the agents alive? | How do the agents get the job done? |

The two compose. A swarm can run on top of a fleet, with each swarm agent being a fleet process and `delegate` routing over the same `POST /chat` API. Delegation also works in-process as a sub-`Engine` with no fleet at all. That is why the two tasks are separable and neither is subordinate to the other. See [fleet.md](fleet.md) for the fleet side of the pattern.

## Building blocks

- **Personas** (`/agent`): per-agent system prompt, session namespace, and optional model override. A persona makes a sub-agent specialized instead of a copy of the caller. Per-agent permission profiles build on this.
- **`delegate(persona, task)` tool**: spawns a sub-agent loop that runs a task with its own persona, session, and model, and returns the result. This is the core swarm primitive.
- **Auditor agents**: sub-agents that review a produced output, such as tests, code review, or fact-checking, instead of producing content themselves.
- **Generate to check to correct**: run a main agent, an auditor, and a fix pass in a loop until the auditor passes.
- **PM/dev/tester orchestration**: multiple specialized agents cooperating on one outcome as a user-facing pattern.

## Personas and delegation

Personas are named agent definitions - a system prompt, optional model override, and optional per-agent tool permissions - stored in a single JSON catalog with bundled, global, and local layers (schema, permission rule, and the bundled default roster in [personas.md](personas.md)). `delegate(persona, task)` spawns a sub-agent that runs the task with the persona's prompt, session, and model, and returns the result. Delegation resolves its permission from the selected persona: a configured persona uses its own `tool_permission` overrides (category `delegate` defaults to `ask`), while a temporary persona created only for parallel work defaults to `deny` until opted in. The bundled catalog ships two pre-carved teams - `researcher`/`writer`/`referencer`/`editor` for documents and `planner`/`programmer`/`tester`/`code-reviewer` for programming - ready to delegate to out of the box.

In-process sub-engines run with a quiet `NullUI` so they never interleave with the caller's REPL, execute synchronously (one sub-agent at a time), and keep their own session (`delegate_<persona>_<ts>` in the shared `sessions/` dir, saved as a complete log). A sub-engine inherits the caller's provider, plugin manager, and worktree; the persona's `system_prompt` becomes the sub-agent's system prompt, its `model` overrides the caller's model when set, and its `tool_permission` overrides are merged on top of the caller's categories. Sub-agents run in `build` mode regardless of the caller's mode, so the persona carve alone decides edit/bash. Ask-gated tools are auto-denied (no interactive confirm), so a sub-agent's effective permissions are exactly the categories its carve allows. The `delegate` tool (category `delegate`) surfaces which persona and task are running, returns the sub-agent's final answer as its result, and - when `delegate_echo` is on (default) - renders the answer plus a sub footer (duration + completion tokens) in the REPL. Live in-REPL progress of a running sub-agent is a deferred enhancement - `Engine.chat()` is a single blocking call and does not yet expose a progress channel; an interactive "jump into the active sub-agent" view is also future work.

A document pipeline is a typical use: a lead agent asks a `researcher` for findings, hands those to a `writer`, has a `referencer` collect citations into a `.bib` file, and runs an `editor` to check the result against the original prompt. This is team orchestration built on personas and delegation.

## In-process vs. cross-process

| | In-process | Cross-process |
|---|---|---|
| Unit | Sub-`Engine` in the same process | Another `replio serve` agent |
| Setup | Spawn a child engine with a persona | Point `delegate` at a sibling agent's `POST /chat` |
| Isolation | Shares the caller's process | Process, worktree, and tool-policy boundaries (see fleet.md) |
| Uses | Auditors, quick subtasks, no fleet required | Team orchestration across scoped folders |

## Security

Sub-agents follow the same tool policy as any agent. In-process sub-engines share the caller's privileges. Cross-process delegation is confined by the target agent's own worktree and `tool_permission` config. Delegated calls go through the same confirm policy as any tool call.