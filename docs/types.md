# Agent types

An agent type is a named agent definition: a system prompt, an optional model override, and optionally a set of skills and per-agent tool permissions. An agent type turns a plain agent into a specialized sub-agent used for swarm delegation (see [swarm.md](swarm.md)). Examples: a `researcher` who does web search and keeps a list of findings, a `writer` who turns those findings into prose, a `referencer` who extracts citations into a `.bib` file, and an `editor` who checks the written text against the original prompt.

## What an agent type bundles

An agent type is a single reusable profile that carries several distinct axes of an agent. The name `type` is deliberately neutral: it means "a kind of agent", so it can hold all of these without privileging any one of them.

| Axis | What it covers | Field |
|---|---|---|
| **Persona** | Identity and behavior - the agent's voice, tone, and communication style | `system_prompt` |
| **Function** | What the agent does - research, writing, review, implementation | `system_prompt` + the type's name and description |
| **Authority** | The scope it may act in - which tools it may use and which are denied | `tool_permission` |
| **Capability** | What it can run on - a model override and attached skills | `model`, `skills` |
| **Expertise** | The domains it is tagged for, used for grouping and filtering | `tags` |
| **Archetype** | A stored, reusable pattern that teams reference as a stage | the registry entry itself |

The bundled catalog ships two pre-carved teams, useful as delegation targets and as templates for your own types (see [teams.md](teams.md)). All leave `model` and `skills` empty (they inherit the caller's model) and differ only in `tool_permission`:

| type | function | tags | edit | bash | web | read |
|---|---|---|---|---|---|---|
| `researcher` | gathers and evaluates web sources, returns findings | research, writing | deny | deny | allow | allow |
| `writer` | turns a findings brief into a document, returns file path | writing | allow | deny | deny | allow |
| `referencer` | resolves citations into a `.bib` file | writing | allow | deny | deny | allow |
| `editor` | auditor: checks a document against the prompt and sources | writing, review | deny | deny | deny | allow |
| `planner` | decomposes a task into an ordered, verifiable plan | programming | deny | deny | allow | allow |
| `programmer` | implements a change and runs the tests until green | programming | allow | allow | deny | allow |
| `tester` | writes and runs tests, reports failures | programming | allow | allow | deny | allow |
| `code-reviewer` | auditor: reviews a change, returns findings | programming, review | deny | allow | deny | allow |

"allow" echoes the caller's category default, "deny" is explicit. Override any type by creating a local (or global) entry with the same `name`.

## Why "type" and not the alternatives

Each natural synonym for this concept covers only part of the profile, or collides with a term already in use in the product:

- **`role`** collides with the chat message roles already in the session format and the provider API (`"role": "user"` / `"assistant"` / `"tool"`). Two "role" concepts in the same API and docs would confuse readers.
- **`function`** collides with OpenAI function calling - the mechanism the agent loop uses to invoke tools.
- **`profile`** collides with the existing "permission profile" language (`tool_permission`).
- **`capability`**, **`mandate`**, **`specialization`**, and **`duty`** each name one axis (what it can do, what it may do, its expertise, its obligation) but not the whole object.
- **`persona`** is the identity-and-behavior axis alone. It is the right word for one axis, but as the name of the whole profile it undersells authority and function, and it reads as marketing jargon to enterprise readers.

`type` appears nowhere else as a user-facing concept in the product (it only shows up as a JSON schema keyword, where it always sits next to a property name and cannot be confused). So "agent type" carries all six axes with no collision, and reads naturally in every usage: "run replio as the researcher agent type", "delegate to the reviewer agent type", "the editor agent type is edit-denied".

## Storage

Agent types come from four layers, merged exactly like config: bundled first, then plugin contributions, then global, then local, with local winning per field. Precedence mirrors bundled plugins (`bundled < plugin < global < local`):

- **Bundled** - the read-only default catalog shipped in the package (`src/replio/bundled_types.json`). Always present, never writable, overridable by any other layer.
- **Plugin** - types contributed by plugins via the `register_types` entry hook (`registry.add_plugin(...)`, see [plugins.md](plugins.md)). An in-memory layer: never written to any `types.json`, refreshed on `/plugins install`/`update`/`uninstall`.
- **Global** - `~/.config/replio/types.json`.
- **Local** - `.replio/types.json`.

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

- `name` - unique key of the type.
- `system_prompt` - the type's system prompt, injected when it runs.
- `model` - optional. Overrides the caller's model when the type runs. Falls back to the caller's model when empty. Accepts a `provider/model` ref (e.g. `opencode-go/deepseek-v4-flash`) to pin provider and model together. A type's model must be approved before it can run (`delegate`/`/team run` ask interactively, or pass `--approve-model` headlessly - see [Model refs and approval](providers.md#model-refs-and-approval)).
- `skills` - optional list of skill names from the [skills registry](skills.md), resolved and injected into the type's sub-agent system prompt (and jobs with `--type`).
- `tags` - optional list of job tags for grouping and filtering (`/type list <tag>`). The bundled set uses a controlled vocabulary: `research`, `writing`, `programming`, `review`.
- `tool_permission` - optional per-agent overrides of `tool_permission` categories. This is the per-agent permission profile.

## Command

`/type` manages the registry:

- `/type` - list agent types, marking each one's origin (`bundled` / `plugin` / `local` / `global` / `merged`) and tags.
- `/type list <tag>` - list only types carrying the tag (e.g. `/type list programming`). Unknown tags print the known tags.
- `/type show <name>` - show a type's full definition.
- `/type new <name> [system prompt]` - create a type in the local catalog (edit the JSON for full fields, including tags). Using an existing name overrides that type.
- `/type remove <name>` - remove a type from the local catalog. Bundled types cannot be removed (override them instead).

## Delegation and permissions

`delegate` resolves its permission from the target type rather than from a single tool-level default:

- A configured type uses its own `tool_permission` overrides. The default for the `delegate` category is `allow` (delegation runs without a prompt). Set `delegate: "ask"` on a type to confirm each delegation to it.
- A temporary type created only to run a task in parallel defaults to `deny` until you opt in.

The rule lets known types delegate freely while keeping every other tool gated as configured, and an administrator can still tighten any type to `ask`.

## Relationship to /agent, skills, and fleets

- `/agent` is the planned interactive way to pick an agent type and run with it. Today you run a type directly through the `delegate` tool (the lead model proposes it, or `/tool delegate {"type": ..., "task": ...}`), which builds the in-process sub-engine from this catalog.
- Skills (a dedicated registry) are a separate capability layer attached to an agent type, distinct from tools and plugins.
- An agent type runs either in-process as a sub-engine (the default for delegation) or as a scoped `replio serve` process in a fleet. In-process variants share the caller's privileges, cross-process variants are confined by the target agent's worktree and `tool_permission` (see [fleet.md](fleet.md)).