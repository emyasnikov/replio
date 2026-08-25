# Personas

A persona is a named agent definition: a system prompt, an optional model override, and optionally a set of skills and per-agent tool permissions. A persona turns a plain agent into a specialized sub-agent used for swarm delegation (see [swarm.md](swarm.md)). Examples: a `researcher` who does web search and keeps a list of findings, a `writer` who turns those findings into prose, a `referencer` who extracts citations into a `.bib` file, and an `editor` who checks the written text against the original prompt.

## Storage

Personas come from three layers, merged exactly like config: bundled first, then global, then local, with local winning per field. Precedence mirrors bundled plugins (`bundled < global < local`):

- **Bundled** - the read-only default catalog shipped in the package (`src/replio/bundled_personas.json`). Always present, never writable, overridable by any other layer.
- **Global** - `~/.config/replio/personas.json`.
- **Local** - `.replio/personas.json`.

Merging is field-by-field for the same `name`: a local or global entry overrides only the fields it sets, so an unset local field (e.g. no `model`) inherits from the layer below.

Schema (per entry):

```json
{
  "name": "researcher",
  "system_prompt": "You are a web researcher. Gather sources, evaluate them, and report findings.",
  "model": "deepseek-r1",
  "skills": [],
  "tool_permission": { "web": "allow", "delegate": "ask" }
}
```

Fields:

- `name` - unique key of the persona.
- `system_prompt` - the persona's system prompt, injected when it runs.
- `model` - optional; overrides the caller's model when the persona runs. Falls back to the caller's model when empty.
- `skills` - optional list of skill names; reserved for the skills registry (see TODO).
- `tool_permission` - optional per-agent overrides of `tool_permission` categories. This is the per-agent permission profile.

## Command

`/persona` manages the registry:

- `/persona` - list personas, marking each one's origin (`local` / `global` / `merged`).
- `/persona show <name>` - show a persona's full definition.
- `/persona new <name> [system prompt]` - create a persona in the local catalog (edit the JSON for full fields).
- `/persona remove <name>` - remove a persona from the local catalog.

## Delegation and permissions

`delegate` resolves its permission from the target persona rather than from a single tool-level default:

- A configured persona uses its own `tool_permission` overrides. The default for the `delegate` category is `ask`.
- A temporary persona created only to run a task in parallel defaults to `deny` until you opt in.

The rule keeps delegated side effects gated like any `ask`-level tool while letting an administrator pre-approve the capabilities of known personas.

## Relationship to /agent, skills, and fleets

- `/agent` is the planned user-facing way to select and run a persona in an interactive session.
- Skills (a dedicated registry) are a separate capability layer attached to a persona, distinct from tools and plugins.
- A persona runs either in-process as a sub-engine (the default for delegation) or as a scoped `replio serve` process in a fleet; in-process variants share the caller's privileges, cross-process variants are confined by the target agent's worktree and `tool_permission` (see [fleet.md](fleet.md)).
