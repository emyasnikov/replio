# Teams

A team is a named, ordered chain of delegated stages - each stage runs under an agent type, and its result is handed to the next stage. A team turns the `delegate` primitive into a repeatable pipeline: "writing" = researcher > writer > referencer > editor for documents, "programming" = planner > programmer > tester > code-reviewer. The registry stores the definition and the sequential stage loop (`Engine.run_team`, `/team run`) executes it.

## Storage

Teams come from four layers, merged exactly like types: bundled first, then plugin contributions, then global, then local, with local winning per field. Precedence is `bundled < plugin < global < local`:

- **Bundled** - the read-only default roster shipped in the package (`src/replio/bundled_teams.json`, the `writing` and `programming` pipelines above).
- **Plugin** - teams contributed by plugins via the `register_teams` entry hook (`registry.add_plugin(...)`, see [plugins.md](plugins.md)). An in-memory layer: never written to any `teams.json`, refreshed on `/plugins install`/`update`/`uninstall`.
- **Global** - `~/.config/replio/teams.json`.
- **Local** - `.replio/teams.json`.

Merging is field-by-field for the same `name`: a local or global entry overrides only the fields it sets, and `stages` is replaced wholesale.

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
- `description` - optional, shown in `/team show`.
- `tags` - optional list for grouping and filtering (`/team list <tag>`), same vocabulary as types.

Stage fields:

- `type` - required, the agent type name (must exist in the [types registry](types.md) at run time, resolved against the same four-layer merge).
- `mode` - optional agent mode override for the stage. Empty inherits the caller. With the sequential stage loop, an explicit mode applies to that stage's sub-engine while the rest of the team follows the caller.
- `task_hint` - optional guidance folded into the delegated brief for this stage.
- `handoff_note` - optional note passed along with the previous stage's result into the next stage's brief.

## Managing teams

- `/team` - list teams, marking each one's origin (`bundled` / `plugin` / `local` / `global` / `merged`) and tags, with the stage chain on the next line.
- `/team list <tag>` - list only teams carrying the tag (e.g. `/team list programming`).
- `/team show <name>` - show a team's full definition (stages, task hints, handoff notes).
- `/team new <name> [description]` - create a team in the local catalog (edit the JSON for stages, tags, and per-stage fields). Using an existing name overrides that team.
- `/team remove <name>` - remove a team from the local catalog. Bundled teams cannot be removed (override them instead).

Plugins contribute teams through the same `register_teams` entry hook that the kit machine (templates, recipes) uses - see [plugins.md](plugins.md).

## Running a team

`Engine.run_team(team, task)` runs the stages one after another through the same in-process sub-engine as `delegate` (`run_subagent`): each stage runs in its own fresh `sub_<ts>_<parent-session>` session, keeps its own type prompt, skills, and permission carve, and the stage `mode` overrides the caller's mode when set (an empty `mode` inherits the caller's). A stage that fails stops the run and the remaining stages do not execute.

The brief handed to each member is built per run from:

- the team name (and description) plus the original task,
- each prior stage's result (a `## Stage N result (<session>)` block, capped at 4000 chars with a truncation marker),
- the previous stage's `handoff_note` as a stage handoff line,
- the shared team memory block, when present,
- the stage's `task_hint` (or a generic "Complete this stage of the task." line).

After the run, the whole team run is summarized - seeded with the previous team memory - and written to **`.replio/teams/<name>/memory.md`** (atomic write, human-editable). The same memory file is read back into the briefs of the next run, so facts from earlier runs carry without the session files growing. If the summarizer fails, a fallback of one line per stage (type, status, first part of the output or error) is stored instead.

`/team run <name> <task>` executes a team from the REPL and prints one line per stage (`<n>. <type> <status> <duration>s`), the final member's result, and the memory file path.

Recurring teams with persistent member sessions (`job`-style warm sessions) and scheduled team runs (`jobs add --team`) are later milestones.