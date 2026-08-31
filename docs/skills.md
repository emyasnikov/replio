# Skills

A skill is a named set of markdown instructions a persona can attach: `Persona.skills` lists skill names, and when that persona runs, each resolved skill's content is injected into its system prompt under a `## Skills` section. Skills are capability instructions distinct from tools and plugins - a persona carries them, the sub-agent reads them.

## Storage

Skills come from three layers, merged like personas and teams: plugin contributions first, then global, then local, with local winning per field:

- **Plugin** - skills contributed by plugins via the `register_skills` entry hook (`registry.add_plugin(...)`, see [plugins.md](plugins.md)). An in-memory layer: never written to `.replio/skills/`, refreshed on `/plugins install`/`update`/`uninstall`.
- **Global** - `~/.config/replio/skills/<name>.md`.
- **Local** - `.replio/skills/<name>.md`.

Each skill is one flat Markdown file: the filename stem is the skill name, the file body is the skill's instructions.

## Schema

```markdown
# finders

Find sources and evaluate them. For each finding include the claim,
the source URL, and a one-line reliability assessment.
```

A skill has:

- `name` - the filename stem (`finders.md` -> `finders`), referenced from `Persona.skills`.
- `content` - the full file body, injected verbatim into the persona's system prompt.
- `description` - optional, defaults to the first line of the content for file-based skills. Plugin contributions may set it explicitly along with `tags`.

Plugin contributions use the same entry shape, with an explicit `content` field:

```python
def register_skills(registry):
    registry.add_plugin({'name': 'finders', 'content': '# finders\n\n...'})
```

## Injection

When a persona with `skills` runs as a sub-agent (`delegate`), each registered skill's content is appended to the persona's system prompt:

```
<persona system prompt>

## Skills

### finders

Find sources and evaluate them. ...
```

Missing or empty skills are skipped silently, and a persona without skills gets an unchanged prompt. Jobs with `--persona` inject the same section (from the global/local file layers - plugin contributions do not reach the scheduler's preparse, same rule as plugin personas there). The injection format is built by `skills_section(registry, names)` in `replio.skills`.

## Managing skills

- `/skill` - list skills (name, first-line description, origin) - `(local)` / `(global)` / `(plugin)` / `(merged)`.
- `/skill show <name>` - print the full skill content.
- `/skill new <name>` - create an empty local skill (edit the created `.md` file, or write one directly).
- `/skill remove <name>` - remove a local skill. Plugin skills cannot be removed (override them locally instead).

The team kit (see [swarm.md](swarm.md)) generates skills as part of its templates and persists them to the local skills dir.