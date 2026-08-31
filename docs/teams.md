# Teams

A team is a named, ordered chain of delegated stages - each stage runs under a persona, and its result is handed to the next stage. A team turns the `delegate` primitive into a repeatable pipeline: "writing" = researcher > writer > referencer > editor for documents, "programming" = planner > programmer > tester > code-reviewer. Teams are shape-only: the registry stores the definition, the sequential stage loop that executes it (`Engine.run_team` and `/team run`) is the next step.

## Storage

Teams come from four layers, merged exactly like personas: bundled first, then plugin contributions, then global, then local, with local winning per field. Precedence is `bundled < plugin < global < local`:

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
        "persona": "researcher",
        "task_hint": "Gather and evaluate sources on the topic.",
        "handoff_note": "Hand the findings list to the writer."
      },
      {
        "persona": "writer",
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
- `stages` - ordered list of stage objects. A stage may also be a plain string (`"researcher"`), shorthand for a stage with only a persona.
- `description` - optional, shown in `/team show`.
- `tags` - optional list for grouping and filtering (`/team list <tag>`), same vocabulary as personas.

Stage fields:

- `persona` - required, the persona name (must exist in the [personas registry](personas.md) at run time, resolved against the same four-layer merge).
- `mode` - optional agent mode override for the stage. Empty inherits the caller. Sub-agents today run in `build` mode, so stage modes become meaningful with the sequential stage loop.
- `task_hint` - optional guidance folded into the delegated brief for this stage.
- `handoff_note` - optional note passed along with the previous stage's result into the next stage's brief.

## Managing teams

- `/team` - list teams, marking each one's origin (`bundled` / `plugin` / `local` / `global` / `merged`) and tags, with the stage chain on the next line.
- `/team list <tag>` - list only teams carrying the tag (e.g. `/team list programming`).
- `/team show <name>` - show a team's full definition (stages, task hints, handoff notes).
- `/team new <name> [description]` - create a team in the local catalog (edit the JSON for stages, tags, and per-stage fields). Using an existing name overrides that team.
- `/team remove <name>` - remove a team from the local catalog. Bundled teams cannot be removed (override them instead).

Plugins contribute teams through the same `register_teams` entry hook that the kit machine (templates, recipes) uses - see [plugins.md](plugins.md). The sequential run loop, generated briefs, and shared team memory land with `Engine.run_team` (see [swarm.md](swarm.md)).