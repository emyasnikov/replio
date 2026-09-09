# Vision

**One terminal, whole teams**

One REPL. One prompt. The lead agent composes a specialized team - types and skills
instantiated from a private template library matching the project description and request -
runs the team stage-by-stage (sequentially first), each member working under its own type,
skills, and permissions, with generated briefs, handoff, and shared memory. Teams are stored,
reused, extended per customer, and scheduled. The composition machinery (templates, generator,
library, authoring commands) lives in a **movable private plugin** (`replio-teamkit`), never in
the core, so internal know-how leaves the repo as one documented unit whenever needed.

## Decisions

- **Sequential-first**: team stages run one member after another via `run_subagent` (existing,
  battle-tested). No concurrency in the first iteration. In-process threaded concurrency is a
  later milestone (cuts wall-clock, not tokens).
- **No pre-saved run prompts**: briefs, handoff, and memory are generated per run. Stored
  artifacts are templates and proven specializations - reusable by design, never regenerated.
- **Cache model**: stored types/skills (never regenerated), generated briefs carrying facts,
  shared team memory file, and persistent member sessions for recurring teams (`job`-style warm
  sessions). One-off runs get fresh `sub_` sessions.
- **Kit layout**: flat `library/` with tags (stack, customer, project-type). Matching by tags +
  request + project description. Generation only of deltas.
- **Core stays thin and publishable**: registries + sequential runner + three plugin hooks.
  Everything customer-specific lives in the kit.

## Context economics (why this costs what it costs)

- Sub-engines are separate `Engine`s - no in-memory context sharing exists. The persistence
  channel is session + memory files.
- Cold starts cost: file re-reads by multiple members, brief duplication. Mitigations:
  facts-in-briefs (not just paths), research stage summarizing into team memory
  (`.replio/teams/<name>/memory.md`), recurring teams keep member sessions warm, one-off teams
  stay fresh and clean.
- Honest limit: per-run redundancy will not go to zero. Sequential wall-clock is accepted.

## Architecture

**Core (thin):**

- `TypeRegistry.reload()`. Plugin hooks `register_types` / `register_teams` /
  `register_skills` in `plugins/manager.py` (mirroring `register_tools`).
- `teams.py` - `Team` (name, description, stages: type, mode, task-hint, handoff-note),
  `TeamRegistry` (`.replio/teams.json` + plugin contributions).
- `skills.py` - `SkillRegistry` (`.replio/skills/*.md` + plugin contributions). AgentType `skills`
  resolved and injected into the sub-agent system prompt.
- `Engine.run_team(team, task)` - sequential stage loop: brief builder (task + prior results +
  memory + stage handoff), `run_subagent`, result collection, memory write. `job.team` field so
  `replio jobs` runs teams on schedule.

**Kit plugin `replio-teamkit` (bundled `plugins/`, movable):**

- `src/plugin.py` registering types/teams/skills templates, tools, commands.
- `templates/` - instantiable type + skill template specs. `recipes/` - example teams (incl.
  the two carved teams as team definitions). `library/` - flat tagged store of proven
  teams/types/skills. `tests/`.
- Generator: stack signature from project description/request (README, manifests) -> tags ->
  matching templates -> AI-generated deltas only (via `engine.chat_nonstreaming`), persisted to
  local `types.json` + `skills/` + `teams.json` (with `reload`).
- Authoring commands (`/teamkit`): init, list, new, match, export, import, and per-customer
  export/splitting.
- Core's `/teams` stays registry + run only.

## Work packages and milestones

The task mapping lives in `PLAN.md` (work packages + milestone checkboxes). The milestones below name the verifiable phases of the swarm/team track.

- **M1 - Skeleton and core hooks**: `PLAN.md` mapping, TODO items under `## Open`, `docs/teamkit.md`
  draft (full authoring + move-out guide), core hooks (reload, teams/skills registries, plugin
  hooks, `run_team` sequential + memory + handoff), kit skeleton (manifest, entry, one template,
  one recipe, tests). Verified: `/teams run` end-to-end + unit tests.
- **M2 - Authoring and template matching**: generator, library store with tags,
  `/teamkit new|match`, project-description matching, generate-deltas-only flow, docs completed.
  Verified: one command composes a new project's team. A second project reuses stored artifacts.
- **M3 - Reuse, scheduling, move-out**: persistent member sessions for recurring teams,
  `jobs add --team`, reuse verified across two projects, kit moved out per the documented
  checklist (own/per-customer repo, `plugins install --global`), bundled copy removed from the
  default plugin set. Verified: full workflow with the kit installed externally.
- **M4 - Autonomous supervisor**: start once, it works on its own - the supervisor delegates
  under its type, asks only when it truly needs a decision (an unanswered ask parks and the run
  resumes on reply), keeps working while the terminal is idle or closed (jobs daemon), and
  reports back (session result + job events over connectors). In-process threaded concurrency
  (a non-blocking background delegate from the live REPL) stays out of scope here, as below.

## TODO.md placement

The swarm/team track is tracked as open tasks at the top of `TODO.md` `## Open` (team kit
plugin, template-based composition, team kit library, sequential team runs, skills registry,
plugin contribution hooks). The skills-registry entry supersedes the earlier draft of the same
name. The teams concept supersedes the earlier "jobs registry" TODO item (see `PLAN.md`). The
autonomous supervisor track (start once, ask only when needed, report back) is milestone M4 in
`PLAN.md`, composing the ask routing, the persisted delegate loop turn, and the jobs
report/approval layer.

## Out of scope (later milestones, listed not planned)

In-process threaded team concurrency and live progress channel, war-room focus view, lead-grant
approvals, generate > check > correct loop, fleet-backed teams, and a plugin download service
for battle-tested kits.
