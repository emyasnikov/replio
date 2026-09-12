# Teams

A team is a named, ordered chain of delegated stages - each runs under an agent type and its result is handed to the next. A team turns the `delegate` primitive into a repeatable pipeline: "writing" = researcher > writer > referencer > editor for documents, "programming" = planner > programmer > tester > code-reviewer. The registry stores the definition and the sequential stage loop (`Engine.run_team`) executes it, reachable from the REPL (`/teams run`), the model (the `team` tool), and the CLI.

## Storage

Teams come from four layers, merged exactly like types: bundled, then plugin, then global, then local, local winning per field. Precedence is `bundled < plugin < global < local`:

- **Bundled** - the read-only default roster shipped in the package (`src/replio/bundled_teams.json`, the `writing` and `programming` pipelines above).
- **Plugin** - teams contributed by plugins via the `register_teams` entry hook (`registry.add_plugin(...)`, see [plugins.md](plugins.md)). An in-memory layer: never written to any `teams.json`, refreshed on `/plugins install`/`update`/`uninstall`.
- **Global** - `~/.config/replio/teams.json`.
- **Local** - `.replio/teams.json`.

Merging is field-by-field for the same `name`: an entry overrides only the fields it sets, and `stages` is replaced wholesale.

## Schema

```json
{
  "writing": {
    "description": "Document pipeline: research, write, reference, edit",
    "tags": ["research", "writing"],
    "stages": [
      {
        "type": "researcher",
        "task_hint": "Gather and evaluate sources on the topic.",
        "handoff_note": "Hand the findings list to the writer."
      },
      {
        "type": "writer",
        "mode": "build",
        "task_hint": "Write the document from the findings list.",
        "handoff_note": "Hand the document path to the referencer."
      }
    ]
  }
}
```

Team fields:

- `name` - unique key (the file/registry key).
- `stages` - ordered list of stage objects. A stage may also be a plain string (`"researcher"`), shorthand for a stage with only an agent type.
- `description` - optional, shown in `/teams show`.
- `tags` - optional list for grouping and filtering (`/teams list <tag>`), same vocabulary as types.
- `warm_sessions` - optional boolean (default false). When true, each stage reuses a persistent member session keyed by `<team>__<stage-type>`, so a role keeps its context across runs (see [Warm member sessions](#warm-member-sessions)). The `team` tool's `warm` argument overrides it per run.
- `loop` - optional review loop over a producer/reviewer stage block (see [Review loop](#review-loop)). Properties: `from`, `until`, `max_iterations`, `verdict`.

Stage fields:

- `type` - required, the agent type name (must exist in the [types registry](types.md) at run time, resolved against the same four-layer merge).
- `mode` - optional agent mode override for the stage. Empty inherits the caller. With the sequential stage loop, an explicit mode applies to that stage's sub-engine while the rest of the team follows the caller.
- `task_hint` - optional guidance folded into the delegated brief for this stage.
- `handoff_note` - optional note passed with the previous stage's result into the next stage's brief.
- `skills` - optional list of skill names added to this stage's type for the run, layered over the type's standing skills (see [skills.md](skills.md)). The `team` tool adds task-wide skills to every stage through its own `skills` argument.
- `session_key` - optional explicit warm-session key for this stage. Set it to pin a member's persistent session independently of `warm_sessions`.

## Managing teams

- `/teams` - list teams, marking each one's origin (`bundled` / `plugin` / `local` / `global` / `merged`) and tags, with the stage chain on the next line.
- `/teams list <tag>` - list only teams carrying the tag (e.g. `/teams list programming`).
- `/teams new <name> [description]` - create a team in the local catalog (edit the JSON for stages, tags, and per-stage fields). Using an existing name overrides that team.
- `/teams remove <name>` - remove a team from the local catalog. Bundled teams cannot be removed (override them instead).
- `/teams show <name>` - show a team's full definition (stages, task hints, handoff notes).

Plugins contribute teams through the same `register_teams` entry hook the kit machine (templates, recipes) uses - see [plugins.md](plugins.md).

## Running a team

`Engine.run_team(team, task)` runs the stages one after another through the same in-process sub-engine as `delegate` (`run_subagent`): each stage runs in its own fresh `sub_<ts>_<parent-session>` session by default, with its own type prompt, skills, and permission carve, and the stage `mode` overrides the caller's when set (an empty `mode` inherits). A failed stage stops the run and the remaining stages do not execute.

The brief handed to each member is built per run from:

- the team name (and description) plus the original task,
- each prior stage's result (a `## Stage N result (<session>)` block, capped at 4000 chars with a truncation marker),
- the previous stage's `handoff_note` as a stage handoff line,
- the shared team memory block, when present,
- the stage's `task_hint` (or a generic "Complete this stage of the task." line).

After the run, the whole team run is summarized - seeded with the previous team memory - and written to **`.replio/teams/<name>/memory.md`** (atomic write, human-editable). The next run reads the same file back into its briefs, so facts from earlier runs carry without the session files growing. If the summarizer fails, a fallback of one line per stage (type, status, first part of the output or error) is stored instead.

`/teams run <name> <task>` executes a team from the REPL and prints one line per stage (`<n>. <type> <status> <duration>s`), the final member's result, and the memory file path.

## Warm member sessions

A stage can instead keep a persistent member session, so the role reuses its context (its "experience") across tasks and review rounds while per-run skills extend it:

- `delegate(type, task, session_key=...)` resumes the agent whose warm session carries that key.
- A team sets `warm_sessions: true` to give every stage a persistent key of `<team>__<stage-type>`, or a stage sets an explicit `session_key`.
- The `team` tool's `warm` argument forces warm member sessions for one run, overriding the team setting.

A warm session is named `sub_<key>` and stored like any other session, so it is listed by `/sessions`, exportable, and resumable. Every call appends the new task and brief to the session, so the member sees its own history. Warm sessions are opt-in: omitting the key keeps the fresh one-off `sub_` behavior, and callers should use a stable key (one per role or per team stage) so different roles do not share a session.

## Review loop

A team can iterate a producer/reviewer block until the review passes or a cap is reached - the generate > check > correct pattern. The team's `loop` names the block by stage type (or zero-based index):

```json
{
  "loop": { "from": "writer", "until": "reviewer", "max_iterations": 3, "verdict": "VERDICT:" }
}
```

- Stages before `from` run once, then the `from..until` block repeats, then stages after `until` run once.
- The `until` stage is the review. It passes when its result contains the verdict marker followed by `PASS` (case-insensitive). The default marker is `VERDICT:`, configurable through `loop.verdict`. A reviewer stage should be told to end with `VERDICT: PASS` or `VERDICT: CHANGES`.
- On the next iteration the producer's brief carries a `## Findings from the previous review` block, and the producer keeps its warm session, so it revises with its own context.
- `max_iterations` (default 3) caps the block. Reaching it without a pass is still a successful run, with the last review as the result.

The loop's producer is forced onto a warm session for the run, so its iterations share context even when the team does not set `warm_sessions`. When `warm_sessions` is true the producer uses the team's persistent key instead, so context also carries across runs.

## The `team` tool

`team(name, task)` is the model-facing entry point (core, like `delegate` and `ask`), so a lead agent can orchestrate a whole pipeline in one call instead of delegating each stage itself. It runs `Engine.run_team` and returns the final stage's answer (or `Error: team "<name>" failed: <reason>`).

- **Permission**: category `delegate`, resolved per invocation like `delegate` - a stage type that sets `delegate: "deny"` disables the team, `"ask"` confirms it, otherwise it runs. Unknown teams and stages with unknown types return a clear error.
- **Ceiling**: each stage's carve is still capped by the caller's `grant_permission` (see [config.md](config.md#permission-authority)). When a stage's requested permissions get clamped, the result carries a `(reduced permissions for: <type>)` note, so a silently degraded run is visible.
- **Depth and cycles**: `run_team` refuses a team already on the current stack (`team_cycle`) and stops at `max_team_depth` nested team runs (default 2, `team_depth`), so a supervisor stage that itself runs teams cannot recurse forever. Both values propagate into sub-engines.

The REPL `/tool team {"name": ..., "task": ...}` runs the same handler through a persisted agent-loop turn (the tool is registered `loop=True`).

Scheduled team runs (`jobs add --team`) and job-style recurring member sessions are later milestones.