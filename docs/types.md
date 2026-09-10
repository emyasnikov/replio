# Agent types

An agent type is a named agent definition: a system prompt, an optional model override, and optional skills and per-agent tool permissions. It turns a plain agent into a specialized sub-agent for swarm delegation (see [swarm.md](swarm.md)). Examples: a `researcher` who searches the web and keeps findings, a `writer` who turns findings into prose, a `referencer` who extracts citations into a `.bib` file, and an `editor` who checks text against the original prompt.

## What an agent type bundles

A type is a single reusable profile carrying several distinct axes of an agent. The name `type` is deliberately neutral - "a kind of agent" - so it holds all of these without privileging any one.

| Axis | What it covers | Field |
|---|---|---|
| **Persona** | Identity and behavior - the agent's voice, tone, and communication style | `system_prompt` |
| **Function** | What the agent does - research, writing, review, implementation | `system_prompt` + the type's name and description |
| **Authority** | The scope it may act in - which tools it may use and which are denied | `tool_permission` |
| **Capability** | What it can run on - a model override and attached skills | `model`, `skills` |
| **Expertise** | The domains it is tagged for, used for grouping and filtering | `tags` |
| **Archetype** | A stored, reusable pattern that teams reference as a stage | the registry entry itself |

The bundled catalog ships two pre-carved teams plus a `leader` supervisor type, useful as delegation targets and as templates (see [teams.md](teams.md)). All leave `model` and `skills` empty (inheriting the caller's model) and differ mainly in `tool_permission` (`leader` also sets `grant_permission`/`ask_policy`):

| type | function | tags | edit | bash | web | read |
|---|---|---|---|---|---|---|
| `code-reviewer` | auditor: reviews a change, returns findings | programming, review | deny | allow | deny | allow |
| `editor` | auditor: checks a document against the prompt and sources | writing, review | deny | deny | deny | allow |
| `leader` | supervisor: coordinates teams and agents, delegates, parks asks | research, writing, programming, review | allow | deny | deny | allow |
| `planner` | decomposes a task into an ordered, verifiable plan | programming | deny | deny | allow | allow |
| `programmer` | implements a change and runs the tests until green | programming | allow | allow | deny | allow |
| `referencer` | resolves citations into a `.bib` file | writing | allow | deny | deny | allow |
| `researcher` | gathers and evaluates web sources, returns findings | research, writing | deny | deny | allow | allow |
| `tester` | writes and runs tests, reports failures | programming | allow | allow | deny | allow |
| `writer` | turns a findings brief into a document, returns file path | writing | allow | deny | deny | allow |

`allow` echoes the caller's category default, `deny` is explicit. Override any type by creating a local (or global) entry with the same `name`.

## Why "type" and not the alternatives

Each synonym covers only part of the profile, or collides with a term already in use:

- **`role`** collides with the chat message roles in the session format and provider API (`"role": "user"` / `"assistant"` / `"tool"`). Two "role" concepts in the same API and docs would confuse readers.
- **`function`** collides with OpenAI function calling - the mechanism the agent loop uses to invoke tools.
- **`profile`** collides with the existing "permission profile" language (`tool_permission`).
- **`capability`**, **`mandate`**, **`specialization`**, and **`duty`** each name one axis (what it can do, what it may do, its expertise, its obligation) but not the whole object.
- **`persona`** names the identity-and-behavior axis alone. It fits one axis, but as the name of the whole profile it undersells authority and function, and reads as marketing jargon to enterprise readers.

`type` appears nowhere else as a user-facing concept (only as a JSON schema keyword, always next to a property name, so it cannot be confused). "Agent type" carries all six axes with no collision and reads naturally in every usage: "run replio as the researcher agent type", "delegate to the reviewer agent type", "the editor agent type is edit-denied".

## Storage

Agent types come from four layers, merged exactly like config: bundled, then plugin, then global, then local, local winning per field. Precedence mirrors bundled plugins (`bundled < plugin < global < local`):

- **Bundled** - the read-only default catalog shipped in the package (`src/replio/bundled_types.json`). Always present, never writable, overridable by any other layer.
- **Plugin** - types contributed by plugins via the `register_types` entry hook (`registry.add_plugin(...)`, see [plugins.md](plugins.md)). An in-memory layer: never written to any `types.json`, refreshed on `/plugins install`/`update`/`uninstall`.
- **Global** - `~/.config/replio/types.json`.
- **Local** - `.replio/types.json`.

Merging is field-by-field for the same `name`: an entry overrides only the fields it sets, so an unset field (e.g. no `model`) inherits from the layer below.

Schema (per entry):

```json
{
  "name": "researcher",
  "system_prompt": "You are a web researcher. Gather sources, evaluate them, and report findings.",
  "model": "deepseek-r1",
  "skills": [],
  "tags": ["research", "writing"],
  "tool_permission": { "web": "allow", "delegate": "allow" },
  "grant_permission": { "web": "allow", "delegate": "allow" },
  "ask_policy": { "permission": "auto", "direction": "human" }
}
```

Fields:

- `name` - unique key of the type.
- `system_prompt` - the type's system prompt, injected when it runs.
- `model` - optional. Overrides the caller's model when the type runs, falls back to the caller's when empty. Accepts a `provider/model` ref (e.g. `opencode-go/deepseek-v4-flash`) to pin provider and model together. The model must be approved before the type runs (`delegate`/`/teams run` ask interactively, or pass `--approve-model` headlessly - see [Model refs and approval](providers.md#model-refs-and-approval)).
- `skills` - optional list of skill names from the [skills registry](skills.md), resolved and injected into the type's sub-agent system prompt (and jobs with `--type`).
- `tags` - optional list of job tags for grouping and filtering (`/types list <tag>`). The bundled set uses a controlled vocabulary: `research`, `writing`, `programming`, `review`.
- `tool_permission` - optional per-agent overrides of `tool_permission` categories. The per-agent permission profile.
- `grant_permission` - optional ceiling on the categories this type may hand down to sub-agents. Defaults to the type's own `tool_permission`, so it never widens delegation unless set explicitly. See [Delegation and permissions](#delegation-and-permissions).
- `ask_policy` - optional per-type override of the `ask` routing by kind (`permission`/`direction`), merged over the config `ask_policy`. See [config.md](config.md#ask_policy).

## Command

`/types` manages the registry:

- `/types` - list agent types, marking each one's origin (`bundled` / `plugin` / `local` / `global` / `merged`) and tags.
- `/types list <tag>` - list only types carrying the tag (e.g. `/types list programming`). Unknown tags print the known tags.
- `/types new <name> [system prompt]` - create a type in the local catalog (edit the JSON for full fields, including tags). Using an existing name overrides that type.
- `/types remove <name>` - remove a type from the local catalog. Bundled types cannot be removed (override them instead).
- `/types show <name>` - show a type's full definition.

## Delegation and permissions

`delegate` resolves its permission from the target type rather than from a single tool-level default:

- A configured type uses its own `tool_permission` overrides. The default for the `delegate` category is `allow` (delegation runs without a prompt). Set `delegate: "ask"` on a type to confirm each delegation to it.
- A temporary type created only to run a task in parallel defaults to `deny` until you opt in.

Sub-agent permissions are bounded by the caller: the effective carve is the caller's `tool_permission`, narrowed by the type's carve and capped by the caller's `grant_permission` ceiling (see [config.md](config.md#permission-authority)). `grant_permission` defaults to the caller's own `tool_permission`, so a type can never grant a sub-agent more than the caller holds. A type that sets `grant_permission` may delegate categories it does not use itself - e.g. a supervisor that denies `edit`/`bash` for itself but allows them in its ceiling can hand them to an `implementer` while never running them. An approved `ask(kind="permission")` request creates a one-shot grant on the asking sub-agent, consumed by the next matching call. The operator may grant `always` for the rest of that sub-agent's run.

## Relationship to /agent, skills, and fleets

- `/agent` is the planned interactive way to pick an agent type and run with it. Today a type runs directly through the `delegate` tool (the lead model proposes it, or `/tool delegate {"type": ..., "task": ...}`), which builds the in-process sub-engine from this catalog.
- Skills (a dedicated registry) are a separate capability layer attached to an agent type, distinct from tools and plugins.
- An agent type runs either in-process as a sub-engine (the default for delegation) or as a scoped `replio serve` process in a fleet. In-process variants share the caller's privileges, cross-process variants are confined by the target agent's worktree and `tool_permission` (see [fleet.md](fleet.md)).