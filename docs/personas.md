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
  "tags": ["research", "writing"],
  "tool_permission": { "web": "allow", "delegate": "allow" }
}
```

Fields:

- `name` - unique key of the persona.
- `system_prompt` - the persona's system prompt, injected when it runs.
- `model` - optional; overrides the caller's model when the persona runs. Falls back to the caller's model when empty.
- `skills` - optional list of skill names; reserved for the skills registry (see TODO).
- `tags` - optional list of job tags for grouping and filtering (`/persona list <tag>`). The bundled set uses a controlled vocabulary: `research`, `writing`, `programming`, `review`.
- `tool_permission` - optional per-agent overrides of `tool_permission` categories. This is the per-agent permission profile.

### Default personas

The bundled catalog ships two pre-carved teams, useful as delegation targets and as templates for your own personas. All leave `model` and `skills` empty (they inherit the caller's model) and differ only in `tool_permission`:

| persona | role | tags | edit | bash | web | read |
|---|---|---|---|---|---|---|
| `researcher` | gathers and evaluates web sources, returns findings | research, writing | deny | deny | allow | allow |
| `writer` | turns a findings brief into a document, returns file path | writing | allow | deny | deny | allow |
| `referencer` | resolves citations into a `.bib` file | writing | allow | deny | deny | allow |
| `editor` | auditor: checks a document against the prompt and sources | writing, review | deny | deny | deny | allow |
| `planner` | decomposes a task into an ordered, verifiable plan | programming | deny | deny | allow | allow |
| `programmer` | implements a change and runs the tests until green | programming | allow | allow | deny | allow |
| `tester` | writes and runs tests, reports failures | programming | allow | allow | deny | allow |
| `code-reviewer` | auditor: reviews a change, returns findings | programming, review | deny | allow | deny | allow |

"allow" echoes the caller's category default; "deny" is explicit. Override any persona by creating a local (or global) entry with the same `name`:

## Command

`/persona` manages the registry:

- `/persona` - list personas, marking each one's origin (`bundled` / `local` / `global` / `merged`) and tags.
- `/persona list <tag>` - list only personas carrying the tag (e.g. `/persona list programming`); unknown tags print the known tags.
- `/persona show <name>` - show a persona's full definition.
- `/persona new <name> [system prompt]` - create a persona in the local catalog (edit the JSON for full fields, including tags). Using an existing name overrides that persona.
- `/persona remove <name>` - remove a persona from the local catalog. Bundled personas cannot be removed (override them instead).

## Delegation and permissions

`delegate` resolves its permission from the target persona rather than from a single tool-level default:

- A configured persona uses its own `tool_permission` overrides. The default for the `delegate` category is `allow` (delegation runs without a prompt); set `delegate: "ask"` on a persona to confirm each delegation to it.
- A temporary persona created only to run a task in parallel defaults to `deny` until you opt in.

The rule lets known personas delegate freely while keeping every other tool gated as configured, and an administrator can still tighten any persona to `ask`.

## Relationship to /agent, skills, and fleets

- `/agent` is the planned interactive way to pick a persona and run with it; today you run a persona directly through the `delegate` tool (the lead model proposes it, or `/tool delegate {"persona": ..., "task": ...}`), which builds the in-process sub-engine from this catalog.
- Skills (a dedicated registry) are a separate capability layer attached to a persona, distinct from tools and plugins.
- A persona runs either in-process as a sub-engine (the default for delegation) or as a scoped `replio serve` process in a fleet; in-process variants share the caller's privileges, cross-process variants are confined by the target agent's worktree and `tool_permission` (see [fleet.md](fleet.md)).
